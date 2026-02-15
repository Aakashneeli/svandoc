function Read-DotEnvFile {
    param(
        [string]$Path
    )

    $map = @{}
    if (-not (Test-Path $Path)) {
        return $map
    }

    Get-Content $Path | ForEach-Object {
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

function Get-DotEnvMap {
    param(
        [string]$PrimaryPath = ".env",
        [string]$FallbackPath = ".env.example",
        [string]$ProfileName = ""
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

    $map = Read-DotEnvFile -Path $resolvedPath

    $selectedProfile = $ProfileName
    if (-not $selectedProfile) {
        $envItem = Get-Item -Path "Env:APP_ENV" -ErrorAction SilentlyContinue
        if ($envItem -and $envItem.Value) {
            $selectedProfile = $envItem.Value.Trim()
        }
    }
    if (-not $selectedProfile -and $map.ContainsKey("APP_ENV")) {
        $selectedProfile = $map["APP_ENV"]
    }
    if (-not $selectedProfile) {
        $selectedProfile = "local"
    }

    if ($selectedProfile -ne "local") {
        $primaryDirectory = Split-Path -Parent $resolvedPath
        if (-not $primaryDirectory) {
            $primaryDirectory = "."
        }
        $profileCandidates = @(
            (Join-Path $primaryDirectory ".env.$selectedProfile"),
            (Join-Path $primaryDirectory ".env.$selectedProfile.example"),
            ".env.$selectedProfile",
            ".env.$selectedProfile.example"
        )
        foreach ($candidate in $profileCandidates) {
            if (-not (Test-Path $candidate)) {
                continue
            }
            $overlay = Read-DotEnvFile -Path $candidate
            foreach ($entry in $overlay.GetEnumerator()) {
                $map[$entry.Key] = $entry.Value
            }
            break
        }
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
