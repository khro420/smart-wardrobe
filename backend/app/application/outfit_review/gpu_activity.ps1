param([string]$TargetIds)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$taskTargets = @{}
foreach($taskId in $TargetIds.Split(',')){ $taskTargets[[int]$taskId]=$true }
Get-Counter -Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -Continuous -ErrorAction SilentlyContinue | ForEach-Object {
 $taskSet=$_
 $taskAll=@($taskSet.CounterSamples)
 $taskInvalid=@($taskAll | Where-Object { $_.Status -notin 0,1 -or [double]::IsNaN($_.CookedValue) -or [double]::IsInfinity($_.CookedValue) -or $_.CookedValue -lt 0 })
 $taskObserved=@($taskAll | ForEach-Object { if($_.InstanceName -match '^pid_(\d+)_'){[int]$Matches[1]} } | Sort-Object -Unique)
 $taskSelected=@($taskSet.CounterSamples | Where-Object { if($_.InstanceName -match '^pid_(\d+)_'){ $taskTargets.ContainsKey([int]$Matches[1]) }else{ $false } })
 $taskValues=@($taskSelected | ForEach-Object { [ordered]@{instance=$_.InstanceName;status=[long]$_.Status;percent=[double]$_.CookedValue} })
 $taskEpoch=([DateTimeOffset]$taskSet.Timestamp).ToUnixTimeMilliseconds()/1000.0
 [ordered]@{version='gpu-engine-activity-1.1.0';time=$taskEpoch;global_counter_count=$taskAll.Count;global_valid=($taskAll.Count -gt 0 -and $taskInvalid.Count -eq 0);requested_ids=@($taskTargets.Keys);observed_gpu_pids=$taskObserved;counter_count=$taskSelected.Count;samples=$taskValues} | ConvertTo-Json -Compress -Depth 5 | ForEach-Object { [Console]::WriteLine($_);[Console]::Out.Flush() }
}
