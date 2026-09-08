param([ValidateSet("codex","claude","open-agent")][string]$Agent="codex",[ValidateSet("user","project")][string]$Scope="user",[switch]$Force,[switch]$DryRun,[switch]$Validate)
$argsList=@("scripts/install.py","--agent",$Agent,"--scope",$Scope)
if($Force){$argsList+="--force"}; if($DryRun){$argsList+="--dry-run"}; if($Validate){$argsList+="--validate"}
python @argsList
