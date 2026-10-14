# One-line install on Windows. From a normal (NOT Administrator) PowerShell, in the folder where you
# keep code:
#
#   irm https://raw.githubusercontent.com/jivinstev/mc-buddy-builder/main/install.ps1 | iex
#
# This is only the part that has to happen before setup can run: it refuses an elevated window,
# installs Git for Windows and Python with winget if they are missing, asks where the project folder
# should go, clones Buddy Builder there, and runs setup.cmd. Everything else (Java 21, Claude Code, the
# GitHub CLI, NeoForge and the "Buddy Builder" launcher profile, naming the mod, the private GitHub
# copy) is tools/buddy/setup.py, the same setup a Mac runs as ./setup, so the two cannot drift apart.
# Then it starts Claude Code in the project. Running it again is safe: what is already there is
# skipped, and setup brings in Buddy Builder updates.
#
# Why each step is here (learned on real PCs, see issue #1):
#   - winget searches every source, and when the Microsoft Store source fails (0x8a15005e, a
#     certificate error behind TLS inspection or on a VM) it installs nothing. So every install names
#     `--source winget`.
#   - In an Administrator window the per-user installs and settings land where the everyday window and
#     Claude Code do not look. So it refuses, and says what it checked: the Administrators role and the
#     window's integrity level (High = elevated).
#   - An install changes PATH in the registry, not in the running window. The script re-reads it, so
#     the next step, and this window afterwards, find the new commands with no new window needed.
#
# Settings, as environment variables set before the line above (all optional):
#   BUDDY_DIR          the project folder; skips the question
#   BUDDY_REF          the branch to clone                 (default: main)
#   BUDDY_REPO         the repository to clone             (default: Buddy Builder on GitHub)
#   BUDDY_SETUP_ARGS   more arguments for setup.cmd, e.g. --yes
#   BUDDY_NO_LAUNCH=1  do not start Claude Code at the end
#   BUDDY_ALLOW_ADMIN=1  run elevated anyway (CI runners are elevated; people should not need this)
#
# It runs inside your own PowerShell window (that is what `| iex` does), so it never calls `exit`,
# which would close the window: it returns, and leaves $global:BUDDY_RESULT = 'ok' or 'failed' for CI.
& {
    # Native commands report through exit codes, checked below. With 'Stop' (some hosts set it, CI
    # does), Windows PowerShell 5.1 would turn their stderr output into a terminating error.
    $ErrorActionPreference = 'Continue'
    $repo = if ($env:BUDDY_REPO) { $env:BUDDY_REPO } else { 'https://github.com/jivinstev/mc-buddy-builder' }
    $ref  = if ($env:BUDDY_REF)  { $env:BUDDY_REF }  else { 'main' }
    $name = 'mc-buddy-builder'
    $global:BUDDY_RESULT = 'failed'

    function Say($msg)  { Write-Host "==> $msg" -ForegroundColor Cyan }
    function Fail($msg) {
        Write-Host ''
        Write-Host '==================================================================' -ForegroundColor Red
        Write-Host "STOPPED: $msg" -ForegroundColor Red
        Write-Host '==================================================================' -ForegroundColor Red
    }

    # Elevated = in the Administrators role, OR a High/System integrity level. The role check alone can
    # miss an elevated window; the integrity level is what "Run as administrator" actually changes.
    # (Where the window starts, e.g. C:\WINDOWS\system32, is no signal: normal windows can start there.)
    function Test-Elevated {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $role = ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        $groups = (whoami /groups 2>$null) | Out-String
        $high = ($groups -match 'S-1-16-12288') -or ($groups -match 'S-1-16-16384')
        $level = if ($high) { 'High (elevated)' } elseif ($groups) { 'Medium (normal)' } else { 'unknown' }
        Write-Host "    user: $($id.Name); Administrators role: $(if ($role) {'yes'} else {'no'}); integrity: $level"
        return ($role -or $high)
    }

    # Where the project goes. BUDDY_DIR wins; a clone you are standing in is used as it is; otherwise
    # ask, offering <this folder>\mc-buddy-builder (or <home>\... when this is a Windows system folder).
    function Get-ProjectDir {
        if ($env:BUDDY_DIR) { return [Environment]::ExpandEnvironmentVariables($env:BUDDY_DIR) }
        $here = (Get-Location).ProviderPath
        if ((Test-Path (Join-Path $here '.git')) -and (Test-Path (Join-Path $here 'tools\buddy\setup.py')) -and (Test-Path (Join-Path $here 'setup.cmd'))) {
            Write-Host "    using the project you are in: $here"
            return $here
        }
        $parent = $here
        if (-not $parent -or ($env:windir -and $parent.StartsWith($env:windir, [StringComparison]::OrdinalIgnoreCase))) { $parent = $HOME }
        $suggest = Join-Path $parent $name
        Write-Host ''
        Write-Host 'Where should the Buddy Builder project folder go? Press Enter for the suggestion, or type a folder.'
        Write-Host '(A folder that already has other things in it gets the project inside it.)'
        $answer = Read-Host "Folder [$suggest]"
        if (-not $answer) { return $suggest }
        $answer = $answer.Trim().Trim('"')
        if ($answer.StartsWith('~')) { $answer = $HOME + $answer.Substring(1) }
        $answer = [Environment]::ExpandEnvironmentVariables($answer)
        if (-not [IO.Path]::IsPathRooted($answer)) { $answer = Join-Path $here $answer }
        # Typed a folder of their own (C:\Users\me\dev)? Put the project in it, as `git clone` would.
        if ((Test-Path $answer) -and -not (Test-Path (Join-Path $answer '.git')) -and (Get-ChildItem -Force $answer | Select-Object -First 1)) {
            $answer = Join-Path $answer $name
        }
        return $answer
    }

    # PATH as a new window would see it (Machine, then User, then Claude Code's ~\.local\bin), keeping
    # anything this window added itself.
    function Update-SessionPath {
        $fresh = @()
        foreach ($scope in 'Machine', 'User') {
            $p = [Environment]::GetEnvironmentVariable('Path', $scope)
            if ($p) { $fresh += $p.Split(';') | Where-Object { $_ } | ForEach-Object { [Environment]::ExpandEnvironmentVariables($_) } }
        }
        $bin = Join-Path $HOME '.local\bin'
        if (Test-Path $bin) { $fresh += $bin }
        $keep = $env:Path.Split(';') | Where-Object { $_ -and ($fresh -notcontains $_) }
        $env:Path = (@($fresh) + @($keep) | Select-Object -Unique) -join ';'
    }

    # Python 3 the way setup.cmd finds it: python3, python, py -3, each only if it really runs Python 3
    # (Windows ships python.exe/python3.exe stubs that only open the Microsoft Store).
    function Test-Python {
        foreach ($c in @(@('python3'), @('python'), @('py', '-3'))) {
            if (Get-Command $c[0] -ErrorAction SilentlyContinue) {
                $pyArgs = @($c | Select-Object -Skip 1) + @('-c', 'import sys; sys.exit(sys.version_info[0] != 3)')
                & $c[0] @pyArgs 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) { return $true }
            }
        }
        return $false
    }

    function Install-WithWinget($what, $id, [scriptblock]$present) {
        Update-SessionPath          # installed from another window? This one's PATH may be old.
        if (& $present) { Write-Host "    $what`: already installed"; return $true }
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Fail "$what is missing and winget is not available. Update 'App Installer' from the Microsoft Store (or install $what yourself), then run this again."
            return $false
        }
        Say "Installing $what (winget: $id). If Windows asks for permission, click Yes."
        winget install -e --source winget --accept-package-agreements --accept-source-agreements --id $id
        Update-SessionPath
        if (& $present) { return $true }
        Fail "$what did not install (winget exit code $LASTEXITCODE). Try it by hand: winget install -e --source winget --id $id"
        return $false
    }

    # ---- 0. not elevated ---------------------------------------------------------------------------
    if ($env:OS -ne 'Windows_NT') { Fail 'this installer is for Windows. On a Mac: git clone the repository, then ./setup'; return }
    Say 'Checking this window'
    if ((Test-Elevated) -and $env:BUDDY_ALLOW_ADMIN -ne '1') {
        Fail ("this PowerShell is running as Administrator. Nothing was installed.`n" +
              "Close it, open PowerShell from the Start menu with a plain click (not `"Run as administrator`"),`n" +
              "and paste the line again. (Installed as Administrator, the tools and settings land where your`n" +
              "normal window and Claude Code do not look.)")
        return
    }

    # ---- 1. what setup itself needs ----------------------------------------------------------------
    Say 'Checking Git and Python'
    if (-not (Install-WithWinget 'Git for Windows' 'Git.Git' { [bool](Get-Command git -ErrorAction SilentlyContinue) })) { return }
    if (-not (Install-WithWinget 'Python 3.12' 'Python.Python.3.12' { Test-Python })) { return }

    # ---- 2. the project ----------------------------------------------------------------------------
    $dir = Get-ProjectDir
    if (Test-Path (Join-Path $dir '.git')) {
        git -C $dir remote get-url upstream 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Say "Using $dir (setup brings in any Buddy Builder updates)"
        } else {
            Say "Updating $dir"
            git -C $dir pull --ff-only
            if ($LASTEXITCODE -ne 0) { Write-Host "    (could not fast-forward $dir; using it as it is)" -ForegroundColor Yellow }
        }
    } elseif ((Test-Path $dir) -and (Get-ChildItem -Force $dir | Select-Object -First 1)) {
        Fail "$dir exists and is not a Buddy Builder project. Move it aside or pick another folder, and run this again."
        return
    } else {
        Say "Downloading Buddy Builder into $dir"
        git clone --branch $ref $repo $dir
        if ($LASTEXITCODE -ne 0) { Fail "git clone of $repo ($ref) failed"; return }
    }

    # ---- 3. setup: Java, Claude Code, gh, NeoForge, the mod's name and the GitHub copy ---------------
    Say 'Running setup'
    Set-Location $dir
    $setupArgs = @()
    if ($env:BUDDY_SETUP_ARGS) { $setupArgs += $env:BUDDY_SETUP_ARGS.Split(' ') | Where-Object { $_ } }
    & (Join-Path $dir 'setup.cmd') @setupArgs
    $setupCode = $LASTEXITCODE
    Update-SessionPath          # what setup installed, visible in this window too
    if ($setupCode -ne 0) {
        Fail "setup stopped (see the lines above). Fix what it says, then run  .\setup.cmd  in $dir"
        return
    }
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Fail 'Claude Code is still not installed (see the notes above). Install it with: winget install -e --source winget --id Anthropic.ClaudeCode'
        return
    }
    $global:BUDDY_RESULT = 'ok'

    # ---- 4. Claude Code ---------------------------------------------------------------------------
    if ($env:BUDDY_NO_LAUNCH -eq '1') {
        Say "Done. To start: cd $dir; claude"
        return
    }
    Say "Starting Claude Code. Next time: open PowerShell, then  cd $dir; claude"
    claude
}
