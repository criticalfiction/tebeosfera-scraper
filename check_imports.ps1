Add-Type -AssemblyName System.Windows.Forms, System.Drawing, System.Core
$asms = [AppDomain]::CurrentDomain.GetAssemblies()
function Exists($ns, $name) {
    foreach ($a in $asms) {
        if ($a.GetType("$ns.$name", $false)) { return $true }
    }
    return $false
}
$bad = 0
foreach ($f in Get-ChildItem "$PSScriptRoot\src\*.py") {
    $text = (Get-Content $f.FullName -Raw) -replace "\\\r?\n\s*", " "
    foreach ($m in [regex]::Matches($text, '(?m)^from (System[\w\.]*) import ([^\r\n#]+)')) {
        $ns = $m.Groups[1].Value
        foreach ($n in $m.Groups[2].Value.Split(',')) {
            $name = ($n.Trim() -split '\s+as\s+')[0].Trim()
            if (-not $name) { continue }
            if (-not (Exists $ns $name)) {
                # may be a sub-namespace, e.g. 'from System import Environment' is a type; skip namespaces
                Write-Output "$($f.Name): $ns.$name NOT FOUND"
                $bad++
            }
        }
    }
}
Write-Output "missing: $bad"
