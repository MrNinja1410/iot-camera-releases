# EduCamAnalyzer - Nuitka Build & Obfuscation Script
# Compiles 1.2.py to standalone .exe with Nuitka

param(
    [switch]$Clean,
    [switch]$SignRelease
)

$ErrorActionPreference = "Stop"

# Configuration
$SourceFile = "1.2.py"
$DistFolder = "dist"
$BuildFolder = "build"
$Version = "1.2.0"  # Update this for each release
$AppName = "EduCamAnalyzer"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔨 $AppName Nuitka Build Pipeline" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Clean previous builds
if ($Clean -or (Test-Path $DistFolder) -or (Test-Path $BuildFolder)) {
    Write-Host "🧹 Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path $DistFolder) { Remove-Item $DistFolder -Recurse -Force }
    if (Test-Path $BuildFolder) { Remove-Item $BuildFolder -Recurse -Force }
    Write-Host "✅ Cleaned" -ForegroundColor Green
}

# Check dependencies
Write-Host ""
Write-Host "📦 Checking dependencies..." -ForegroundColor Yellow

$deps = @("nuitka", "zstandard")
foreach ($dep in $deps) {
    $installed = pip list | Select-String $dep
    if (-not $installed) {
        Write-Host "❌ Missing: $dep" -ForegroundColor Red
        Write-Host "Install with: pip install $dep" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ $dep" -ForegroundColor Green
}

# Build with Nuitka
Write-Host ""
Write-Host "🔨 Building with Nuitka..." -ForegroundColor Yellow
Write-Host "Options: --onefile, --windows-console-mode=disable, --remove-output" -ForegroundColor Cyan
Write-Host ""

$nuitkaArgs = @(
    "$SourceFile",
    "--onefile",                                   # Single .exe
    "--output-dir=$DistFolder",                    # Output directory
    "--build-dir=$BuildFolder",                    # Build artifacts
    "--assume-yes-for-downloads",                  # Auto-download MSVCRuntime
    "--windows-console-mode=disable",              # No console window
    "--remove-output",                             # Clean build artifacts after compile
    "--low-memory",                                # Lower memory usage
    "-O",                                          # Optimize
    "--follow-all-imports"                         # Bundle all imports
)

# Obfuscation: variable/function name mangling (Nuitka paid feature alternative: strip comments)
$nuitkaArgs += @(
    "--remove-comments"
)

# Run Nuitka
$nuitkaCmd = "nuitka " + ($nuitkaArgs -join " ")
Write-Host "Command: $nuitkaCmd" -ForegroundColor DarkGray
Write-Host ""

& nuitka $nuitkaArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Nuitka build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Build complete!" -ForegroundColor Green

# Rename output
$outputExe = Get-ChildItem $DistFolder -Filter "1.2.exe" -ErrorAction SilentlyContinue
if ($outputExe) {
    $releaseName = "$AppName-$Version.exe"
    Rename-Item $outputExe.FullName -NewName $releaseName -Force
    $releasePath = Join-Path $DistFolder $releaseName
    Write-Host "📦 Release: $releasePath" -ForegroundColor Cyan

    # Show file info
    $fileInfo = Get-Item $releasePath
    $sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    Write-Host "   Size: $sizeMB MB" -ForegroundColor Cyan
    Write-Host ""

    # Sign release (optional - requires server/sign_release.py)
    if ($SignRelease) {
        Write-Host "🔐 Signing release for auto-update manifest..." -ForegroundColor Yellow
        $signCmd = "cd server && python sign_release.py --sign `"$releasePath`" --version $Version --url https://your-site/dl/$releaseName --notes `"Geolocation feature + improvements`""
        Write-Host "Command: $signCmd" -ForegroundColor DarkGray
        Write-Host "(Set your release URL in sign_release.py)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Could not find output .exe" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Done!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test: $releasePath" -ForegroundColor White
Write-Host "  2. Upload to release server" -ForegroundColor White
Write-Host "  3. Sign for auto-update: build.ps1 -SignRelease" -ForegroundColor White
Write-Host "  4. Push release to GitHub:" -ForegroundColor White
Write-Host "     git tag -a v$Version -m 'Release $Version'" -ForegroundColor White
Write-Host "     git push origin v$Version" -ForegroundColor White
