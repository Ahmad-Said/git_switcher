# Git Profile Switcher — User Installer
# Run with:
#   irm https://raw.githubusercontent.com/Ahmad-Said/git_switcher/main/install.ps1 | iex
#
# Does NOT require administrator rights.
# Installs to:  %LOCALAPPDATA%\GitSwitcher\GitSwitcher.exe
# Shortcuts  :  Start Menu  (always)
#               Desktop     (asked — default yes)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Repo       = 'Ahmad-Said/git_switcher'
$AppName    = 'GitSwitcher'
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$ExePath    = Join-Path $InstallDir "$AppName.exe"
$ApiUrl     = "https://api.github.com/repos/$Repo/releases/latest"

function Write-Step([string]$msg) {
    Write-Host "`n>> $msg" -ForegroundColor Cyan
}

function Write-OK([string]$msg) {
    Write-Host "   OK  $msg" -ForegroundColor Green
}

function Write-Warn([string]$msg) {
    Write-Host "   !! $msg" -ForegroundColor Yellow
}

# ── Resolve latest release ────────────────────────────────────────────────────
Write-Step "Fetching latest release from GitHub..."

try {
    $headers = @{ 'User-Agent' = 'GitSwitcher-Installer'; 'Accept' = 'application/vnd.github+json' }
    $release = Invoke-RestMethod -Uri $ApiUrl -Headers $headers -UseBasicParsing
} catch {
    Write-Error "Could not reach GitHub API: $_"
    exit 1
}

$tag   = $release.tag_name
$asset = $release.assets | Where-Object { $_.name -match '\.exe$' } | Select-Object -First 1

if (-not $asset) {
    Write-Error "No .exe asset found in release $tag."
    exit 1
}

$DownloadUrl = $asset.browser_download_url
Write-OK "Latest release : $tag"
Write-OK "Asset          : $($asset.name)  ($([math]::Round($asset.size/1MB,1)) MB)"

# ── Check if already installed / up-to-date ──────────────────────────────────
if (Test-Path $ExePath) {
    Write-Step "Existing installation found at $ExePath"
    # Read version from the installed binary's ProductVersion (set by PyInstaller)
    $installed = (Get-Item $ExePath).VersionInfo.ProductVersion
    if ($installed -and ("v$installed" -eq $tag -or $installed -eq $tag)) {
        Write-Host "`n  Already up to date ($tag). Nothing to do." -ForegroundColor Green
        exit 0
    }
    Write-Warn "Installed: $installed  ->  Updating to: $tag"
}

# ── Download ──────────────────────────────────────────────────────────────────
Write-Step "Downloading $($asset.name)..."

$TmpFile = Join-Path $env:TEMP "$AppName`_update_$tag.exe"

try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add('User-Agent', 'GitSwitcher-Installer')
    # Show progress via events
    $received = 0
    $total    = $asset.size
    Register-ObjectEvent -InputObject $wc -EventName DownloadProgressChanged -SourceIdentifier DL_Progress -Action {
        $pct = $Event.SourceEventArgs.ProgressPercentage
        $done = [math]::Round($Event.SourceEventArgs.BytesReceived / 1MB, 1)
        $tot  = [math]::Round($Event.SourceEventArgs.TotalBytesToReceive / 1MB, 1)
        Write-Progress -Activity "Downloading $using:AppName $using:tag" `
                       -Status "$done / $tot MB" `
                       -PercentComplete $pct
    } | Out-Null

    $wc.DownloadFile($DownloadUrl, $TmpFile)
    Unregister-Event -SourceIdentifier DL_Progress -ErrorAction SilentlyContinue
    Write-Progress -Activity "Downloading" -Completed
} catch {
    Unregister-Event -SourceIdentifier DL_Progress -ErrorAction SilentlyContinue
    Write-Progress -Activity "Downloading" -Completed
    Write-Error "Download failed: $_"
    exit 1
}
Write-OK "Downloaded to $TmpFile"

# ── Install ───────────────────────────────────────────────────────────────────
Write-Step "Installing to $InstallDir ..."

if (-not (Test-Path $InstallDir)) {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
}

# If the target exe is running, ask user to close it.
$retries = 0
while ($true) {
    try {
        Copy-Item -Path $TmpFile -Destination $ExePath -Force
        break
    } catch [System.IO.IOException] {
        if ($retries -ge 10) {
            Write-Error "Cannot write to $ExePath — is $AppName still running? Close it and retry."
            exit 1
        }
        if ($retries -eq 0) {
            Write-Warn "$AppName appears to be running. Close it to continue... (waiting up to 30 s)"
        }
        Start-Sleep -Seconds 3
        $retries++
    }
}

Remove-Item -Path $TmpFile -Force -ErrorAction SilentlyContinue
Write-OK "Installed $ExePath"

# ── Register app path (user-level, no admin) ──────────────────────────────────
try {
    $appPathsKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\$AppName.exe"
    if (-not (Test-Path $appPathsKey)) {
        New-Item -Path $appPathsKey -Force | Out-Null
    }
    Set-ItemProperty -Path $appPathsKey -Name '(default)' -Value $ExePath
    Set-ItemProperty -Path $appPathsKey -Name 'Path'      -Value $InstallDir
    Write-OK "App path registered in registry (user scope)"
} catch {
    Write-Warn "Could not register app path (non-fatal): $_"
}

# ── Start Menu shortcut ───────────────────────────────────────────────────────
Write-Step "Creating Start Menu shortcut..."

$startMenuDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$lnkPath      = Join-Path $startMenuDir "$AppName.lnk"

try {
    $shell = New-Object -ComObject WScript.Shell
    $lnk   = $shell.CreateShortcut($lnkPath)
    $lnk.TargetPath       = $ExePath
    $lnk.WorkingDirectory = $InstallDir
    $lnk.Description      = 'Git Profile Switcher'
    $lnk.Save()
    Write-OK "Start Menu: $lnkPath"
} catch {
    Write-Warn "Could not create Start Menu shortcut: $_"
}

# ── Desktop shortcut (optional) ───────────────────────────────────────────────
$desktopLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) "$AppName.lnk"

$createDesktop = $true
if ($Host.UI.RawUI -and -not [Environment]::GetEnvironmentVariable('CI')) {
    # Only prompt when running interactively
    $answer = Read-Host "`nCreate a Desktop shortcut? [Y/n]"
    $createDesktop = ($answer -eq '' -or $answer -match '^[Yy]')
}

if ($createDesktop) {
    try {
        $shell = New-Object -ComObject WScript.Shell
        $lnk   = $shell.CreateShortcut($desktopLnk)
        $lnk.TargetPath       = $ExePath
        $lnk.WorkingDirectory = $InstallDir
        $lnk.Description      = 'Git Profile Switcher'
        $lnk.Save()
        Write-OK "Desktop:    $desktopLnk"
    } catch {
        Write-Warn "Could not create Desktop shortcut: $_"
    }
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ✓  Git Profile Switcher $tag installed successfully!" -ForegroundColor Green
Write-Host "     Launch from the Start Menu or run:  $ExePath" -ForegroundColor Gray
Write-Host ""

