param(
    [string]$InputPath = "TAI_LIEU_BAO_VE_DU_AN.md",
    [string]$OutputPath = "TAI_LIEU_BAO_VE_DU_AN.docx"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Escape-Xml([string]$Value) {
    if ($null -eq $Value) { return "" }
    return [System.Security.SecurityElement]::Escape($Value)
}

function Inline-Runs([string]$Text) {
    $builder = [System.Text.StringBuilder]::new()
    $pattern = '(\*\*[^*]+\*\*|`[^`]+`)'
    $parts = [regex]::Split($Text, $pattern)
    foreach ($part in $parts) {
        if (-not $part) { continue }
        $properties = ""
        $value = $part
        if ($part.StartsWith("**") -and $part.EndsWith("**")) {
            $value = $part.Substring(2, $part.Length - 4)
            $properties = '<w:rPr><w:b/></w:rPr>'
        } elseif ($part.StartsWith('`') -and $part.EndsWith('`')) {
            $value = $part.Substring(1, $part.Length - 2)
            $properties = '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="19"/></w:rPr>'
        }
        [void]$builder.Append('<w:r>')
        [void]$builder.Append($properties)
        [void]$builder.Append('<w:t xml:space="preserve">')
        [void]$builder.Append((Escape-Xml $value))
        [void]$builder.Append('</w:t></w:r>')
    }
    return $builder.ToString()
}

function Paragraph-Xml([string]$Text, [string]$Style = "Normal", [bool]$KeepNext = $false) {
    $keep = if ($KeepNext) { '<w:keepNext/>' } else { '' }
    return '<w:p><w:pPr><w:pStyle w:val="' + $Style + '"/>' + $keep + '</w:pPr>' + (Inline-Runs $Text) + '</w:p>'
}

function Code-Paragraph-Xml([string]$Text) {
    return '<w:p><w:pPr><w:pStyle w:val="Code"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">' + (Escape-Xml $Text) + '</w:t></w:r></w:p>'
}

function Table-Xml([object[]]$Rows) {
    $builder = [System.Text.StringBuilder]::new()
    [void]$builder.Append('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr>')
    for ($rowIndex = 0; $rowIndex -lt $Rows.Count; $rowIndex++) {
        [void]$builder.Append('<w:tr>')
        foreach ($cell in $Rows[$rowIndex]) {
            $cellText = ($cell -replace '\*\*', '' -replace '`', '').Trim()
            $runProperties = if ($rowIndex -eq 0) { '<w:rPr><w:b/></w:rPr>' } else { '' }
            $shade = if ($rowIndex -eq 0) { '<w:shd w:fill="D9EAF7"/>' } else { '' }
            [void]$builder.Append('<w:tc><w:tcPr>' + $shade + '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar></w:tcPr><w:p><w:r>' + $runProperties + '<w:t xml:space="preserve">' + (Escape-Xml $cellText) + '</w:t></w:r></w:p></w:tc>')
        }
        [void]$builder.Append('</w:tr>')
    }
    [void]$builder.Append('</w:tbl><w:p/>')
    return $builder.ToString()
}

function Add-ZipText($Archive, [string]$Name, [string]$Content) {
    $entry = $Archive.CreateEntry($Name, [System.IO.Compression.CompressionLevel]::Optimal)
    $stream = $entry.Open()
    try {
        $utf8 = [System.Text.UTF8Encoding]::new($false)
        $writer = [System.IO.StreamWriter]::new($stream, $utf8)
        try { $writer.Write($Content) } finally { $writer.Dispose() }
    } finally {
        $stream.Dispose()
    }
}

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
$lines = [System.IO.File]::ReadAllLines($resolvedInput, [System.Text.Encoding]::UTF8)
$body = [System.Text.StringBuilder]::new()
$inCode = $false
$index = 0

while ($index -lt $lines.Length) {
    $line = $lines[$index]
    if ($line -eq '<!-- PAGE BREAK -->') {
        [void]$body.Append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        $index++
        continue
    }
    if ($line.StartsWith('```')) {
        $inCode = -not $inCode
        $index++
        continue
    }
    if ($inCode) {
        [void]$body.Append((Code-Paragraph-Xml $line))
        $index++
        continue
    }
    if ($line.StartsWith('|') -and ($index + 1 -lt $lines.Length) -and $lines[$index + 1] -match '^\|[\s:\-|]+\|$') {
        $rows = [System.Collections.Generic.List[object]]::new()
        $rows.Add(@($line.Trim('|').Split('|') | ForEach-Object { $_.Trim() }))
        $index += 2
        while ($index -lt $lines.Length -and $lines[$index].StartsWith('|')) {
            $rows.Add(@($lines[$index].Trim('|').Split('|') | ForEach-Object { $_.Trim() }))
            $index++
        }
        [void]$body.Append((Table-Xml $rows.ToArray()))
        continue
    }
    if ($line -match '^(#{1,3})\s+(.+)$') {
        $level = $matches[1].Length
        $style = if ($level -eq 1) { 'Heading1' } elseif ($level -eq 2) { 'Heading2' } else { 'Heading3' }
        [void]$body.Append((Paragraph-Xml $matches[2] $style $true))
    } elseif ($line -match '^[-*]\s+(.+)$') {
        [void]$body.Append((Paragraph-Xml ('• ' + $matches[1]) 'ListBullet'))
    } elseif ($line -match '^\d+\.\s+(.+)$') {
        [void]$body.Append((Paragraph-Xml ($line) 'ListNumber'))
    } elseif ($line -match '^>\s+(.+)$') {
        [void]$body.Append((Paragraph-Xml $matches[1] 'Quote'))
    } elseif ([string]::IsNullOrWhiteSpace($line)) {
        [void]$body.Append('<w:p/>')
    } else {
        [void]$body.Append((Paragraph-Xml $line))
    }
    $index++
}

$documentXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
'<w:body>' + $body.ToString() +
'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1417" w:header="567" w:footer="567"/><w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>' +
'</w:body></w:document>'

$stylesXml = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="26"/><w:lang w:val="vi-VN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:before="600" w:after="360"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="17365D"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:pageBreakBefore/><w:spacing w:before="280" w:after="160"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="17365D"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="1F4E78"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="180" w:after="100"/></w:pPr><w:rPr><w:b/><w:i/><w:sz w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567" w:hanging="284"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="ListNumber"><w:name w:val="List Number"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567" w:hanging="284"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567" w:right="567"/><w:spacing w:before="120" w:after="120"/></w:pPr><w:rPr><w:i/><w:color w:val="595959"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="284"/><w:spacing w:after="0"/><w:shd w:fill="F2F2F2"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr></w:style>
  <w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="B4C6E7"/><w:left w:val="single" w:sz="4" w:color="B4C6E7"/><w:bottom w:val="single" w:sz="4" w:color="B4C6E7"/><w:right w:val="single" w:sz="4" w:color="B4C6E7"/><w:insideH w:val="single" w:sz="4" w:color="D9E2F3"/><w:insideV w:val="single" w:sz="4" w:color="D9E2F3"/></w:tblBorders></w:tblPr></w:style>
</w:styles>
'@

$contentTypes = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
'@

$rootRels = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'@

$documentRels = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
'@

$now = [DateTime]::UtcNow.ToString("s") + "Z"
$coreXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Tài liệu bảo vệ dự án chữ ký số RSA</dc:title><dc:subject>Ký và xác thực văn bản bằng RSA-SHA256</dc:subject><dc:creator>Codex</dc:creator><cp:keywords>RSA; SHA-256; chữ ký số; Flask; PDF</cp:keywords><dcterms:created xsi:type="dcterms:W3CDTF">' + $now + '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">' + $now + '</dcterms:modified></cp:coreProperties>'
$appXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office Word</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><Company></Company><AppVersion>16.0000</AppVersion></Properties>'

if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}
$fileStream = [System.IO.File]::Open($resolvedOutput, [System.IO.FileMode]::CreateNew)
try {
    $archive = [System.IO.Compression.ZipArchive]::new($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        Add-ZipText $archive '[Content_Types].xml' $contentTypes
        Add-ZipText $archive '_rels/.rels' $rootRels
        Add-ZipText $archive 'word/document.xml' $documentXml
        Add-ZipText $archive 'word/styles.xml' $stylesXml
        Add-ZipText $archive 'word/_rels/document.xml.rels' $documentRels
        Add-ZipText $archive 'docProps/core.xml' $coreXml
        Add-ZipText $archive 'docProps/app.xml' $appXml
    } finally {
        $archive.Dispose()
    }
} finally {
    $fileStream.Dispose()
}

Write-Output "Created: $resolvedOutput"
