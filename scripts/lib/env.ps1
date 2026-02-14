function Get-DotEnvMap {
    param(
        [string]$PrimaryPath = ".env",
        [string]$FallbackPath = ".env.example"
    )

    $resolvedPath = $null
    if (Test-Path $PrimaryPath) {
        $resolvedPath = $PrimaryPath
    } elseif (Test-Path $FallbackPath) {
        $resolvedPath = $FallbackPath
    }

    if (-not $resolvedPath) {
        throw "No environment file found. Expected $PrimaryPath or $FallbackPath."
    }

    $map = @{}
    Get-Content $resolvedPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        if (-not $line.Contains("=")) { return }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        $map[$key] = $value
    }
    return $map
}

function Get-EnvValue {
    param(
        [hashtable]$Map,
        [string]$Key,
        [string]$DefaultValue = ""
    )

    if ($Map.ContainsKey($Key) -and $Map[$Key] -ne "") {
        return $Map[$Key]
    }

    $envItem = Get-Item -Path ("Env:{0}" -f $Key) -ErrorAction SilentlyContinue
    if ($envItem -and $envItem.Value -ne "") {
        return $envItem.Value
    }

    return $DefaultValue
}
