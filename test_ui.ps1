# Runs test_ui.py with ComicRack CE's own IronPython (Windows PowerShell 5.1,
# .NET Framework, STA thread - the same environment the plugin runs in).
$cr = 'C:\Program Files\ComicRack Community Edition'
Add-Type -Path "$cr\Microsoft.Scripting.dll"
Add-Type -Path "$cr\Microsoft.Dynamic.dll"
Add-Type -Path "$cr\IronPython.dll"
Add-Type -Path "$cr\IronPython.Modules.dll"

$out = Join-Path $PSScriptRoot 'build\ui-test'
New-Item -ItemType Directory -Force $out | Out-Null

$engine = [IronPython.Hosting.Python]::CreateEngine()
$sys = [IronPython.Hosting.Python]::GetSysModule($engine)
$argv = New-Object IronPython.Runtime.List
$argv.append('test_ui.py'); $argv.append((Join-Path $PSScriptRoot 'src')); $argv.append($out)
$sys.argv = $argv

# send Python's stdout to this console
$stream = New-Object System.IO.MemoryStream
$engine.Runtime.IO.SetOutput($stream, [Text.Encoding]::UTF8)
try {
    $engine.ExecuteFile((Join-Path $PSScriptRoot 'test_ui.py')) | Out-Null
} catch {
    # GetService is generic (GetService<T>), which PowerShell 5.1 can't call
    # directly, so it's called through reflection.
    $err = $_.Exception
    if ($err.InnerException) { $err = $err.InnerException }
    $getService = $engine.GetType().GetMethod('GetService').MakeGenericMethod(
        [Microsoft.Scripting.Hosting.ExceptionOperations])
    $ops = $getService.Invoke($engine, @(, [object[]]@()))
    Write-Output ('PYTHON ERROR: ' + $ops.FormatException($err))
}
[Text.Encoding]::UTF8.GetString($stream.ToArray())
"screenshots in $out"
