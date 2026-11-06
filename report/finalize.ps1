# Open the report in Word, fill in the table of contents, save it, and export a PDF copy.
$docx = Join-Path $PSScriptRoot "Driver_Behaviour_Report.docx"
$pdf = Join-Path $PSScriptRoot "Driver_Behaviour_Report.pdf"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($docx)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    $doc.ExportAsFixedFormat([string]$pdf, 17)   # 17 = PDF
    $doc.Close()
    "saved $pdf"
}
finally {
    $word.Quit()
}
