[CmdletBinding()]
param(
    [string]$Out
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Errors = [System.Collections.Generic.List[string]]::new()

$OperatingSystem = $null
try {
    $OperatingSystemRecord = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
    $OperatingSystem = [ordered]@{
        family = "Windows"
        caption = [string]$OperatingSystemRecord.Caption
        version = [string]$OperatingSystemRecord.Version
        architecture = [string]$OperatingSystemRecord.OSArchitecture
    }
}
catch {
    $Errors.Add("OPERATING_SYSTEM_INVENTORY_FAILED")
}

$Processors = @()
try {
    $Processors = @(
        Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop |
            ForEach-Object {
                [ordered]@{
                    name = [string]$_.Name
                    physical_cores = [int]$_.NumberOfCores
                    logical_threads = [int]$_.NumberOfLogicalProcessors
                    max_clock_mhz = [int]$_.MaxClockSpeed
                }
            } |
            Sort-Object -Property name, physical_cores, logical_threads, max_clock_mhz
    )
}
catch {
    $Errors.Add("CPU_INVENTORY_FAILED")
}

$MemoryModules = @()
[long]$TotalPhysicalBytes = 0
try {
    $MemoryModules = @(
        Get-CimInstance -ClassName Win32_PhysicalMemory -ErrorAction Stop |
            ForEach-Object {
                [ordered]@{
                    capacity_bytes = [long]$_.Capacity
                    configured_clock_mhz = [int]$_.ConfiguredClockSpeed
                }
            } |
            Sort-Object -Property capacity_bytes, configured_clock_mhz
    )
    foreach ($Module in $MemoryModules) {
        $TotalPhysicalBytes += [long]$Module["capacity_bytes"]
    }
}
catch {
    $Errors.Add("MEMORY_INVENTORY_FAILED")
}

$GraphicsAdapters = @()
try {
    $GraphicsAdapters = @(
        Get-CimInstance -ClassName Win32_VideoController -ErrorAction Stop |
            ForEach-Object {
                [ordered]@{
                    name = [string]$_.Name
                    adapter_ram_bytes = if ($null -eq $_.AdapterRAM) { $null } else { [long]$_.AdapterRAM }
                    driver_version = if ($null -eq $_.DriverVersion) { $null } else { [string]$_.DriverVersion }
                }
            } |
            Sort-Object -Property name, driver_version
    )
}
catch {
    $Errors.Add("GPU_INVENTORY_FAILED")
}

$NvidiaSmi = Get-Command -Name "nvidia-smi" -CommandType Application -ErrorAction SilentlyContinue
$Report = [ordered]@{
    schema_version = "1.0"
    ok = ($Errors.Count -eq 0)
    labels = @(
        "INVENTORY_ONLY"
        "NOT_PERFORMANCE_EVIDENCE"
        "NOT_DFT_ENGINE_EXECUTION"
    )
    external_dft_engine_invoked = $false
    performance_qualification = "NOT_ELIGIBLE"
    platform = $OperatingSystem
    cpu = $Processors
    memory = [ordered]@{
        module_count = $MemoryModules.Count
        total_physical_bytes = $TotalPhysicalBytes
        modules = $MemoryModules
    }
    graphics = $GraphicsAdapters
    tool_availability = [ordered]@{
        nvidia_smi = if ($null -eq $NvidiaSmi) { "NOT_AVAILABLE" } else { "AVAILABLE" }
        powershell = "AVAILABLE"
        python = if ($null -eq (Get-Command -Name "python" -CommandType Application -ErrorAction SilentlyContinue)) {
            "NOT_AVAILABLE"
        }
        else {
            "AVAILABLE"
        }
    }
    privacy = [ordered]@{
        hostname_recorded = $false
        username_recorded = $false
        home_path_recorded = $false
        environment_values_recorded = $false
        executable_paths_recorded = $false
    }
    errors = @($Errors)
}

$Rendered = $Report | ConvertTo-Json -Depth 8
if ($Out) {
    $Destination = [System.IO.Path]::GetFullPath($Out)
    $Directory = [System.IO.Path]::GetDirectoryName($Destination)
    if (-not [string]::IsNullOrWhiteSpace($Directory)) {
        [System.IO.Directory]::CreateDirectory($Directory) | Out-Null
    }
    $Temporary = "$Destination.tmp-$([System.Guid]::NewGuid().ToString('N'))"
    try {
        [System.IO.File]::WriteAllText(
            $Temporary,
            $Rendered + [System.Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false)
        )
        Move-Item -LiteralPath $Temporary -Destination $Destination -Force
    }
    finally {
        if (Test-Path -LiteralPath $Temporary) {
            Remove-Item -LiteralPath $Temporary -Force
        }
    }
}

Write-Output $Rendered
if ($Report.ok) {
    exit 0
}
exit 1
