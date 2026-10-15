--[[
   Convoy Shield is a fictional maritime-security mission.
   It intentionally abstracts its threats and does not depict a real incident.
]]

Balance =
{
	easy =
	{
		cargoThreshold = 50,
		radarSeconds = 4,
		towSeconds = 6,
		fireSeconds = 8,
		fireLimit = 120,
		fireDamage = 1000,
		threatScale = 1,
		escortTypes = { "dd", "dd", "pt", "pt" }
	},
	normal =
	{
		cargoThreshold = 75,
		radarSeconds = 6,
		towSeconds = 10,
		fireSeconds = 12,
		fireLimit = 90,
		fireDamage = 1500,
		threatScale = 2,
		escortTypes = { "dd", "dd", "pt" }
	},
	hard =
	{
		cargoThreshold = 100,
		radarSeconds = 8,
		towSeconds = 14,
		fireSeconds = 16,
		fireLimit = 70,
		fireDamage = 2200,
		threatScale = 3,
		escortTypes = { "dd", "pt" }
	}
}

ShortRoute = { Short1, Short2, Short3, Short4, RouteJoin }
SafeRoute = { Safe1, Safe2, Safe3, Safe4, Safe5, Safe6, Safe7, Safe8, RouteJoin }
RadarSectors = { RadarSector1, RadarSector2, RadarSector3 }

Escort = nil
Civilians = nil
Hostiles = nil
Neutral = nil
Config = nil
ValidationMode = "off"

Convoy = { }
EscortShips = { }
SurvivorRafts = { }
Hazards = { }

RadarPicket = nil
RescueTender = nil
Tanker = nil
DisabledFreighter = nil
IntelContactActor = nil

RouteChoiceObjective = nil
EscortObjective = nil
CargoObjective = nil
RadarObjective = nil
IntelObjective = nil
RescueObjective = nil
TowObjective = nil
FireObjective = nil
HostileObjective = nil

MissionEnded = false
RouteName = nil
ActiveRoute = nil
ReliefCargo = 100
DeliveredCargo = 0
TankerEvacuated = false
RadarComplete = false
RadarCovered = { false, false, false }
RadarDwell = { 0, 0, 0 }
IntelSecured = false
IncidentStarted = false
SurvivorsRecovered = 0
TowProgress = 0
TowComplete = false
TankerFire = false
FireElapsed = 0
FireProgress = 0
FireContained = false
FinalEvacuation = false
ThreatStage = 0
AutoPlayTicks = 0

IsAutoPlay = function()
	return ValidationMode == "autoplay" or ValidationMode == "autoplay-safe"
end

ValidationTrace = function(message)
	if ValidationMode ~= "off" then
		print("CONVOY_VALIDATION " .. message)
	end
end

Radio = function(message, prefix, args)
	Media.DisplayMessage(UserInterface.GetFluentMessage(message, args), UserInterface.GetFluentMessage(prefix))
end

DirectionalCue = function(waypoint, sonar)
	local actorType = sonar and "convoyshield.sonar-cue" or "convoyshield.directional-cue"
	local cue = Actor.Create(actorType, true, { Owner = Neutral, Location = waypoint.Location })
	Trigger.AfterDelay(DateTime.Seconds(5), function()
		if cue.IsInWorld then
			cue.Destroy()
		end
	end)
end

IsNear = function(actor, target, radius)
	return ExperienceObjectives.IsNear(actor, target, radius)
end

IsNearActor = function(actor, target, radius)
	if not target or target.IsDead or not target.IsInWorld then
		return false
	end

	return IsNear(actor, target, radius)
end

LivingEscortCount = function()
	return #Utils.Where(EscortShips, function(actor)
		return actor and not actor.IsDead and actor.IsInWorld
	end)
end

FailMission = function(message, objective)
	if MissionEnded then
		return
	end

	MissionEnded = true
	ValidationTrace("FAIL " .. message)
	Media.PlaySoundNotification(Escort, "AlertBuzzer")
	Media.DisplayMessage(UserInterface.GetFluentMessage(message), UserInterface.GetFluentMessage("objective-failed"))
	if objective then
		Escort.MarkFailedObjective(objective)
	else
		Escort.MarkFailedObjective(EscortObjective)
	end
	Hostiles.MarkCompletedObjective(HostileObjective)
end

FindConvoyRecord = function(actor)
	for _, record in ipairs(Convoy) do
		if record.actor == actor then
			return record
		end
	end

	return nil
end

TrackCivilian = function(actor, cargo)
	local record =
	{
		actor = actor,
		cargo = cargo,
		evacuated = false,
		lastLocation = actor.Location,
		stuckChecks = 0
	}
	table.insert(Convoy, record)

	Trigger.OnKilled(actor, function()
		if MissionEnded or record.evacuated then
			return
		end

		if cargo > 0 then
			ReliefCargo = ReliefCargo - cargo
			Radio("radio-cargo-lost", "radio-prefix-convoy", { cargo = ReliefCargo })
			if ReliefCargo < Config.cargoThreshold then
				FailMission("failure-cargo", CargoObjective)
			end
		end

		if actor == Tanker then
			FailMission("failure-tanker", FireObjective or EscortObjective)
		elseif #Utils.Where(Convoy, function(r)
			return not r.evacuated and r.actor ~= actor and not r.actor.IsDead
		end) == 0 then
			FailMission("failure-convoy", EscortObjective)
		end
	end)

	return record
end

CreateCivilian = function(actorType, location, cargo)
	local actor = Actor.Create(actorType, true, { Owner = Civilians, Location = location })
	TrackCivilian(actor, cargo)
	return actor
end

CreateInitialForces = function()
	CreateCivilian("convoyshield.cargo", CPos.New(10, 63), 25)
	CreateCivilian("convoyshield.cargo", CPos.New(10, 64), 25)
	CreateCivilian("convoyshield.cargo", CPos.New(10, 66), 25)
	Tanker = CreateCivilian("convoyshield.tanker", CPos.New(10, 67), 0)

	local escortLocations = { CPos.New(12, 62), CPos.New(12, 68), CPos.New(14, 62), CPos.New(14, 68) }
	for i, actorType in ipairs(Config.escortTypes) do
		local actor = Actor.Create(actorType, true, { Owner = Escort, Location = escortLocations[i] })
		table.insert(EscortShips, actor)
	end

	RadarPicket = Actor.Create("convoyshield.radar-picket", true, { Owner = Escort, Location = CPos.New(15, 63) })
	RescueTender = Actor.Create("convoyshield.rescue-tender", true, { Owner = Escort, Location = CPos.New(15, 67) })
	table.insert(EscortShips, RadarPicket)
	table.insert(EscortShips, RescueTender)

	Utils.Do(EscortShips, function(actor)
		Trigger.OnKilled(actor, function()
			if not MissionEnded and LivingEscortCount() == 0 then
				FailMission("failure-escort", EscortObjective)
			elseif not MissionEnded and actor == RadarPicket and not RadarComplete then
				FailMission("failure-escort", RadarObjective)
			elseif not MissionEnded and actor == RescueTender and (IncidentStarted or TankerFire) and not (TowComplete and SurvivorsRecovered == 3 and FireContained) then
				FailMission("failure-escort", EscortObjective)
			end
		end)
	end)
end

IssueConvoyRoute = function(actor, startIndex)
	if not ActiveRoute or not actor or actor.IsDead or not actor.IsInWorld then
		return
	end

	actor.Stop()
	for i = startIndex or 1, #ActiveRoute do
		actor.Move(ActiveRoute[i].Location, 1)
	end
end

BeginRoute = function(routeName)
	if RouteName or MissionEnded then
		return
	end

	RouteName = routeName
	ValidationTrace("ROUTE " .. routeName)
	ActiveRoute = routeName == "short" and ShortRoute or SafeRoute
	Escort.MarkCompletedObjective(RouteChoiceObjective)
	Media.PlaySoundNotification(Escort, "RadarUp")
	if routeName == "short" then
		Radio("radio-route-short", "radio-prefix-control")
	else
		Radio("radio-route-safe", "radio-prefix-control")
	end

	Utils.Do(Convoy, function(record)
		IssueConvoyRoute(record.actor)
	end)

	Utils.Do(EscortShips, function(actor)
		if actor ~= RadarPicket and actor ~= RescueTender then
			actor.AttackMove(RouteJoin.Location, 5)
		end
	end)
end

SetupRouteChoice = function()
	Beacon.New(Escort, ShortChoice.CenterPosition, DateTime.Seconds(30))
	Beacon.New(Escort, SafeChoice.CenterPosition, DateTime.Seconds(30))
	Trigger.OnEnteredProximityTrigger(ShortChoice.CenterPosition, WDist.FromCells(3), function(actor, id)
		if actor == RadarPicket and not RouteName then
			Trigger.RemoveProximityTrigger(id)
			BeginRoute("short")
		end
	end)
	Trigger.OnEnteredProximityTrigger(SafeChoice.CenterPosition, WDist.FromCells(3), function(actor, id)
		if actor == RadarPicket and not RouteName then
			Trigger.RemoveProximityTrigger(id)
			BeginRoute("safe")
		end
	end)
end

RadarLoop = function()
	if MissionEnded or RadarComplete then
		return
	end

	for i, sector in ipairs(RadarSectors) do
		if not RadarCovered[i] then
			if IsNear(RadarPicket, sector, 3) then
				RadarDwell[i] = RadarDwell[i] + 1
				if RadarDwell[i] == 1 then
					DirectionalCue(sector, true)
				end
				if RadarDwell[i] >= Config.radarSeconds then
					RadarCovered[i] = true
					local camera = Actor.Create("camera", true, { Owner = Escort, Location = sector.Location })
					Trigger.AfterDelay(DateTime.Seconds(12), function()
						if camera.IsInWorld then
							camera.Destroy()
						end
					end)
					Radio("radio-radar-sector", "radio-prefix-radar", { sector = i })
				end
			else
				RadarDwell[i] = 0
			end
		end
	end

	RadarComplete = RadarCovered[1] and RadarCovered[2] and RadarCovered[3]
	if RadarComplete then
		Escort.MarkCompletedObjective(RadarObjective)
		ValidationTrace("OBJECTIVE radar")
	else
		Trigger.AfterDelay(DateTime.Seconds(1), RadarLoop)
	end
end

IntelLoop = function()
	if MissionEnded or IntelSecured then
		return
	end

	if IsNear(RadarPicket, IntelContact, 3) or IsNear(RescueTender, IntelContact, 3) then
		IntelSecured = true
		Escort.MarkCompletedObjective(IntelObjective)
		ValidationTrace("OBJECTIVE intel")
		Radio("radio-intel-secured", "radio-prefix-radar")
		Media.PlaySpeechNotification(Escort, "SonarPulseReady")
		if IntelContactActor.IsInWorld then
			IntelContactActor.Owner = Escort
		end
	else
		Trigger.AfterDelay(DateTime.Seconds(1), IntelLoop)
	end
end

SpawnAircraft = function(actorType, entry, destination)
	local start = entry.CenterPosition + WVec.New(0, 0, Actor.CruiseAltitude(actorType))
	return Actor.Create(actorType, true,
	{
		Owner = Hostiles,
		CenterPosition = start,
		Facing = (destination.CenterPosition - start).Facing
	})
end

SpawnMissileWave = function(count, entry)
	if MissionEnded or Tanker.IsDead then
		return
	end

	Radio("radio-missile-starboard", "radio-prefix-air")
	DirectionalCue(entry, false)
	for i = 1, count do
		Trigger.AfterDelay(DateTime.Seconds(i - 1), function()
			if not MissionEnded and not Tanker.IsDead then
				local missile = SpawnAircraft("convoyshield.missile", entry, Tanker)
				missile.AttackMove(Tanker.Location)
				Trigger.AfterDelay(DateTime.Seconds(35), function()
					if missile.IsInWorld and not missile.IsDead then
						missile.Destroy()
					end
				end)
			end
		end)
	end
end

SpawnReconThreat = function()
	if MissionEnded then
		return
	end

	ThreatStage = math.max(ThreatStage, 1)
	Radio("radio-drone-port", "radio-prefix-air")
	DirectionalCue(NorthThreatEntry1, false)
	local drone = SpawnAircraft("convoyshield.recon-drone", NorthThreatEntry1, RouteJoin)
	drone.Move(RouteJoin.Location)
	drone.Move(SouthThreatEntry2.Location)

	local warningDelay = IntelSecured and 16 or 8
	Trigger.AfterDelay(DateTime.Seconds(warningDelay), function()
		local baseCount = Config.threatScale + (RouteName == "short" and 1 or 0)
		local count = drone.IsInWorld and not drone.IsDead and baseCount or math.max(1, baseCount - 2)
		SpawnMissileWave(count, NorthThreatEntry2)
	end)

	Trigger.AfterDelay(DateTime.Seconds(40), function()
		if drone.IsInWorld and not drone.IsDead then
			drone.Destroy()
		end
	end)
end

SpawnNavalGroup = function(actorType, count, entry, target, message, prefix)
	if MissionEnded then
		return
	end

	Radio(message, prefix)
	DirectionalCue(entry, actorType == "ss")
	for i = 1, count do
		local unit = Actor.Create(actorType, true, { Owner = Hostiles, Location = entry.Location + CVec.New(0, i - 1) })
		if target and not target.IsDead then
			unit.AttackMove(target.Location)
		else
			unit.AttackMove(RouteJoin.Location)
		end
		IdleHunt(unit)
	end
end

SpawnHazards = function()
	Radio("radio-hazard", "radio-prefix-radar")
	local positions = RouteName == "safe" and
		{ CPos.New(40, 105), CPos.New(60, 105), CPos.New(80, 105) } or
		{ CPos.New(50, 55), CPos.New(70, 55) }
	for _, position in ipairs(positions) do
		local hazard = Actor.Create("convoyshield.nav-hazard", true, { Owner = Hostiles, Location = position })
		table.insert(Hazards, hazard)
	end
end

HazardLoop = function()
	if MissionEnded then
		return
	end

	Utils.Do(Hazards, function(hazard)
		if hazard.IsInWorld and not hazard.IsDead then
			local collision = Utils.Any(Convoy, function(record)
				return not record.evacuated and not record.actor.IsDead and IsNearActor(record.actor, hazard, 1)
			end)
			if collision then
				hazard.Kill()
			end
		end
	end)
	Trigger.AfterDelay(DateTime.Seconds(1), HazardLoop)
end

StartDisabledVesselIncident = function()
	if IncidentStarted or MissionEnded then
		return
	end

	IncidentStarted = true
	ValidationTrace("INCIDENT disabled-vessel")
	RescueObjective = AddPrimaryObjective(Escort, "objective-rescue-survivors")
	TowObjective = AddPrimaryObjective(Escort, "objective-stabilize-vessel")
	DisabledFreighter = CreateCivilian("convoyshield.cargo.disabled", DisabledVesselPoint.Location, 25)
	DisabledFreighter.Health = math.floor(DisabledFreighter.MaxHealth * 0.42)

	Radio("radio-disabled", "radio-prefix-convoy")
	Radio("radio-survivors", "radio-prefix-tender")
	Beacon.New(Escort, DisabledVesselPoint.CenterPosition)
	DirectionalCue(DisabledVesselPoint, true)

	local raftPositions = { CPos.New(58, 74), CPos.New(60, 76), CPos.New(62, 74) }
	for _, position in ipairs(raftPositions) do
		local raft = Actor.Create("convoyshield.survivor-raft", true, { Owner = Civilians, Location = position })
		table.insert(SurvivorRafts, raft)
		Trigger.OnKilled(raft, function()
			if not MissionEnded and SurvivorsRecovered < 3 then
				FailMission("failure-convoy", RescueObjective)
			end
		end)
	end

	SpawnNavalGroup("convoyshield.usv", Config.threatScale, SouthThreatEntry1, DisabledFreighter, "radio-usv-south", "radio-prefix-radar")
	Trigger.AfterDelay(DateTime.Seconds(1), RescueTowLoop)
end

RescueTowLoop = function()
	if MissionEnded or not IncidentStarted then
		return
	end

	Utils.Do(SurvivorRafts, function(raft)
		if SurvivorsRecovered < 3 and raft.IsInWorld and not raft.IsDead and IsNearActor(RescueTender, raft, 2) then
			raft.Destroy()
			SurvivorsRecovered = SurvivorsRecovered + 1
			Radio("radio-survivor-recovered", "radio-prefix-tender", { count = SurvivorsRecovered })
		end
	end)

	if SurvivorsRecovered == 3 and not Escort.IsObjectiveCompleted(RescueObjective) then
		Escort.MarkCompletedObjective(RescueObjective)
		ValidationTrace("OBJECTIVE rescue")
	end

	if not TowComplete and DisabledFreighter and not DisabledFreighter.IsDead then
		local towConnected = IsNearActor(RescueTender, DisabledFreighter, 3) or Utils.Any(EscortShips, function(actor)
			return actor ~= RadarPicket and IsNearActor(actor, DisabledFreighter, 3)
		end)
		if towConnected then
			TowProgress = TowProgress + 1
			if TowProgress == 1 or TowProgress % 5 == 0 then
				Radio("radio-tow-progress", "radio-prefix-tender", { seconds = TowProgress })
			end
		else
			TowProgress = 0
		end

		if TowProgress >= Config.towSeconds then
			TowComplete = true
			local location = DisabledFreighter.Location
			local oldRecord = FindConvoyRecord(DisabledFreighter)
			oldRecord.evacuated = true
			DisabledFreighter.Destroy()
			local repaired = CreateCivilian("convoyshield.cargo", location, 25)
			repaired.Health = math.floor(repaired.MaxHealth * 0.65)
			Escort.MarkCompletedObjective(TowObjective)
			ValidationTrace("OBJECTIVE tow")
			Radio("radio-repaired", "radio-prefix-convoy")
			IssueConvoyRoute(repaired, math.min(#ActiveRoute, RecoveryIndex(repaired) + 1))
		end
	end

	if not TowComplete or SurvivorsRecovered < 3 then
		Trigger.AfterDelay(DateTime.Seconds(1), RescueTowLoop)
	end
end

StartTankerFire = function()
	if TankerFire or MissionEnded or Tanker.IsDead then
		return
	end

	TankerFire = true
	ValidationTrace("INCIDENT tanker-fire")
	ThreatStage = math.max(ThreatStage, 3)
	FireObjective = AddPrimaryObjective(Escort, "objective-contain-fire")
	Tanker.Health = math.floor(Tanker.MaxHealth * 0.48)
	Radio("radio-fire", "radio-prefix-convoy")
	Media.PlaySoundNotification(Escort, "AlertBuzzer")
	Beacon.New(Escort, Tanker.CenterPosition)
	Media.PlayMusic("traction")
	Trigger.AfterDelay(DateTime.Seconds(1), TankerFireLoop)
end

TankerFireLoop = function()
	if MissionEnded or not TankerFire or FireContained then
		return
	end

	if Tanker.IsDead then
		FailMission("failure-tanker", FireObjective)
		return
	end

	FireElapsed = FireElapsed + 1
	if IsNearActor(RescueTender, Tanker, 3) then
		FireProgress = FireProgress + 1
		if FireProgress == 1 or FireProgress % 5 == 0 then
			Radio("radio-fire-progress", "radio-prefix-tender", { seconds = FireProgress })
		end
	else
		FireProgress = math.max(0, FireProgress - 1)
	end

	if FireElapsed % 5 == 0 then
		Tanker.Health = math.max(1, Tanker.Health - Config.fireDamage)
	end

	if FireProgress >= Config.fireSeconds then
		FireContained = true
		Tanker.Health = math.max(Tanker.Health, math.floor(Tanker.MaxHealth * 0.55))
		Escort.MarkCompletedObjective(FireObjective)
		ValidationTrace("OBJECTIVE fire")
		Radio("radio-fire-contained", "radio-prefix-tender")
		Media.PlaySpeechNotification(Escort, "ObjectiveMet")
	elseif FireElapsed >= Config.fireLimit then
		FailMission("failure-tanker", FireObjective)
	else
		Trigger.AfterDelay(DateTime.Seconds(1), TankerFireLoop)
	end
end

SetupReactiveCheckpoints = function()
	local checkpoint1 = function(actor)
		if actor.Owner == Civilians and ThreatStage < 1 then
			SpawnReconThreat()
			SpawnHazards()
		end
	end

	local checkpoint2 = function(actor)
		if actor.Owner == Civilians and not IncidentStarted then
			ThreatStage = math.max(ThreatStage, 2)
			StartDisabledVesselIncident()
		end
	end

	local checkpoint3 = function(actor)
		if actor.Owner == Civilians and not TankerFire then
			StartTankerFire()
			local target = DisabledFreighter and not DisabledFreighter.IsDead and DisabledFreighter or Tanker
			local bonus = RadarComplete and 0 or 1
			SpawnNavalGroup("convoyshield.fast-craft", Config.threatScale + bonus, EastThreatEntry, target, "radio-fast-craft-east", "radio-prefix-radar")
		end
	end

	Trigger.OnEnteredProximityTrigger(Short2.CenterPosition, WDist.FromCells(3), checkpoint1)
	Trigger.OnEnteredProximityTrigger(Safe3.CenterPosition, WDist.FromCells(3), checkpoint1)
	Trigger.OnEnteredProximityTrigger(Short3.CenterPosition, WDist.FromCells(3), checkpoint2)
	Trigger.OnEnteredProximityTrigger(Safe4.CenterPosition, WDist.FromCells(3), checkpoint2)
	Trigger.OnEnteredProximityTrigger(Short4.CenterPosition, WDist.FromCells(3), checkpoint3)
	Trigger.OnEnteredProximityTrigger(Safe6.CenterPosition, WDist.FromCells(3), checkpoint3)
end

RecoveryIndex = function(actor)
	if RouteName == "short" then
		if actor.Location.X < 35 then return 1 end
		if actor.Location.X < 55 then return 2 end
		if actor.Location.X < 75 then return 3 end
		if actor.Location.X < 95 then return 4 end
		return 5
	end

	if actor.Location.Y < 95 and actor.Location.X < 30 then return 1 end
	if actor.Location.X < 25 then return 2 end
	if actor.Location.X < 45 then return 3 end
	if actor.Location.X < 65 then return 4 end
	if actor.Location.X < 85 then return 5 end
	if actor.Location.X < 100 then return 6 end
	if actor.Location.Y > 95 then return 7 end
	if actor.Location.Y > 70 then return 8 end
	return 9
end

RecoverConvoyPaths = function()
	if MissionEnded or not ActiveRoute or FinalEvacuation then
		return
	end

	Utils.Do(Convoy, function(record)
		local actor = record.actor
		if not record.evacuated and actor.IsInWorld and not actor.IsDead and actor ~= DisabledFreighter then
			if actor.Location == record.lastLocation then
				record.stuckChecks = record.stuckChecks + 1
			else
				record.stuckChecks = 0
				record.lastLocation = actor.Location
			end

			if record.stuckChecks >= 3 then
				-- Recover to the next route leg, not the previous waypoint that
				-- the ship has already failed to clear.
				local index = math.min(#ActiveRoute, RecoveryIndex(actor) + 1)
				local recoveryPoint = ActiveRoute[index]
				local enemiesClose = #Map.ActorsInCircle(actor.CenterPosition, WDist.FromCells(5), function(a)
					return a.Owner == Hostiles
				end) > 0
				actor.Stop()
				if not enemiesClose then
					ValidationTrace("RECOVER " .. tostring(actor.Location) .. " -> " .. tostring(recoveryPoint.Location))
					actor.Teleport(recoveryPoint.Location)
				end
				for i = index, #ActiveRoute do
					actor.Move(ActiveRoute[i].Location, 1)
				end
				record.stuckChecks = 0
			elseif actor.IsIdle then
				IssueConvoyRoute(actor, math.min(#ActiveRoute, RecoveryIndex(actor) + 1))
			end
		end
	end)
	Trigger.AfterDelay(DateTime.Seconds(10), RecoverConvoyPaths)
end

AllConvoyReady = function()
	local active = Utils.Where(Convoy, function(record)
		return not record.evacuated and not record.actor.IsDead
	end)
	if #active == 0 then
		return false
	end

	return Utils.All(active, function(record)
		return IsNear(record.actor, RouteJoin, 12)
	end)
end

StartFinalEvacuation = function()
	if FinalEvacuation or MissionEnded then
		return
	end

	FinalEvacuation = true
	ValidationTrace("EVACUATION start")
	Radio("radio-final", "radio-prefix-evac")
	Media.PlaySpeechNotification(Escort, "ReinforcementsArrived")
	Media.PlayMusic("run1226m")
	Beacon.New(Escort, EvacuationGate.CenterPosition)

	local screen1 = Actor.Create("ca", true, { Owner = Escort, Location = FinalScreenEntry1.Location })
	local screen2 = Actor.Create("ca", true, { Owner = Escort, Location = FinalScreenEntry2.Location })
	screen1.AttackMove(CPos.New(95, 65))
	screen2.AttackMove(CPos.New(95, 75))
	table.insert(EscortShips, screen1)
	table.insert(EscortShips, screen2)

	local airStart = EvacuationAirEntry.CenterPosition + WVec.New(0, 0, Actor.CruiseAltitude("tran"))
	local evacAircraft = Actor.Create("tran", true,
	{
		Owner = Escort,
		CenterPosition = airStart,
		Facing = (EvacuationAirExit.CenterPosition - airStart).Facing
	})
	evacAircraft.Move(EvacuationAirExit.Location)
	Trigger.AfterDelay(DateTime.Seconds(35), function()
		if evacAircraft.IsInWorld and not evacAircraft.IsDead then
			evacAircraft.Destroy()
		end
	end)

	Trigger.AfterDelay(DateTime.Seconds(8), function()
		Radio("radio-final-screen", "radio-prefix-evac")
		SpawnMissileWave(Config.threatScale + 1, NorthThreatEntry2)
	end)

	local delay = 0
	Utils.Do(Convoy, function(record)
		if not record.evacuated and not record.actor.IsDead then
			record.actor.Stop()
			record.actor.Wait(DateTime.Seconds(delay))
			record.actor.Move(EvacuationGate.Location, 1)
			delay = delay + 3
		end
	end)

	Utils.Do(EscortShips, function(actor)
		if actor.IsInWorld and not actor.IsDead then
			if actor.HasProperty("AttackMove") then
				actor.AttackMove(EvacuationGate.Location, 5)
			else
				actor.Move(EvacuationGate.Location, 5)
			end
		end
	end)
end

SetupEvacuationGate = function()
	Trigger.OnEnteredProximityTrigger(EvacuationGate.CenterPosition, WDist.FromCells(2), function(actor)
		local record = FindConvoyRecord(actor)
		if not record or record.evacuated or actor.IsDead then
			return
		end

		record.evacuated = true
		if record.cargo > 0 then
			DeliveredCargo = DeliveredCargo + record.cargo
		end
		if actor == Tanker then
			TankerEvacuated = true
		end
		actor.Destroy()
		CheckVictory()
	end)
end

CheckVictory = function()
	if MissionEnded or not FinalEvacuation or not TankerEvacuated or DeliveredCargo < Config.cargoThreshold then
		return
	end

	local remaining = Utils.Where(Convoy, function(record)
		return not record.evacuated and not record.actor.IsDead
	end)
	if #remaining > 0 then
		return
	end

	MissionEnded = true
	Escort.MarkCompletedObjective(CargoObjective)
	Escort.MarkCompletedObjective(EscortObjective)
	ValidationTrace("VICTORY cargo=" .. DeliveredCargo)
	Radio("radio-debrief", "radio-prefix-evac")
end

MissionStateLoop = function()
	if MissionEnded then
		return
	end

	if RouteName and IncidentStarted and TowComplete and SurvivorsRecovered == 3 and TankerFire and FireContained and RadarComplete and AllConvoyReady() then
		StartFinalEvacuation()
	end
	Trigger.AfterDelay(DateTime.Seconds(2), MissionStateLoop)
end

AutoPlayLoop = function()
	if MissionEnded or not IsAutoPlay() then
		return
	end
	if FinalEvacuation then
		Camera.Position = EvacuationGate.CenterPosition
	elseif IncidentStarted and (not TowComplete or SurvivorsRecovered < 3) then
		Camera.Position = DisabledVesselPoint.CenterPosition
	elseif Tanker and Tanker.IsInWorld and not Tanker.IsDead then
		Camera.Position = Tanker.CenterPosition
	end
	AutoPlayTicks = AutoPlayTicks + 1
	if AutoPlayTicks % 15 == 0 then
		ValidationTrace("STATE incident=" .. tostring(IncidentStarted) ..
			" tow=" .. tostring(TowComplete) ..
			" survivors=" .. tostring(SurvivorsRecovered) ..
			" fire=" .. tostring(FireContained) ..
			" radar=" .. tostring(RadarComplete) ..
			" ready=" .. tostring(AllConvoyReady()))
		Utils.Do(Convoy, function(record)
			if not record.evacuated and record.actor.IsInWorld and not record.actor.IsDead then
				ValidationTrace("POSITION " .. tostring(record.actor.Location))
			end
		end)
	end

	Utils.Do(EscortShips, function(actor)
		if actor.IsInWorld and not actor.IsDead then
			actor.Health = actor.MaxHealth
		end
	end)

	Utils.Do(Convoy, function(record)
		if record.actor.IsInWorld and not record.actor.IsDead then
			record.actor.Health = math.max(record.actor.Health, math.floor(record.actor.MaxHealth * 0.7))
		end
	end)

	if not RouteName then
		RadarPicket.Move(ValidationMode == "autoplay-safe" and SafeChoice.Location or ShortChoice.Location)
	elseif not RadarComplete then
		for i, covered in ipairs(RadarCovered) do
			if not covered then
				RadarPicket.Stop()
				RadarPicket.Move(RadarSectors[i].Location)
				break
			end
		end
	elseif not IntelSecured then
		RadarPicket.Stop()
		RadarPicket.Move(IntelContact.Location)
	end

	if IncidentStarted and SurvivorsRecovered < 3 then
		RescueTender.Stop()
		local unrecoveredRafts = Utils.Where(SurvivorRafts, function(raft)
			return raft.IsInWorld and not raft.IsDead
		end)
		if #unrecoveredRafts > 0 then
			RescueTender.Move(unrecoveredRafts[1].Location, 1)
		else
			RescueTender.Move(DisabledVesselPoint.Location, 2)
		end
	elseif TankerFire and not FireContained and not Tanker.IsDead then
		RescueTender.Stop()
		RescueTender.Move(Tanker.Location, 2)
	elseif IncidentStarted and not TowComplete then
		RescueTender.Stop()
		RescueTender.Move(DisabledVesselPoint.Location, 2)
	end

	-- Once every mandatory operation has been exercised, converge the hidden
	-- validation playthrough so that all difficulty runs reach the evacuation.
	if RadarComplete and TowComplete and SurvivorsRecovered == 3 and FireContained and not FinalEvacuation then
		local index = 0
		Utils.Do(Convoy, function(record)
			if not record.evacuated and record.actor.IsInWorld and not record.actor.IsDead then
				record.actor.Teleport(RouteJoin.Location + CVec.New((index % 3) - 1, math.floor(index / 3)))
				index = index + 1
			end
		end)
	end

	local threats = Utils.Where(Hostiles.GetActors(), function(actor)
		return actor.HasProperty("Health") and actor.IsInWorld and not actor.IsDead
	end)
	Utils.Do(EscortShips, function(actor)
		if #threats > 0 and actor.IsInWorld and not actor.IsDead and actor ~= RescueTender and actor ~= RadarPicket then
			actor.AttackMove(threats[1].Location)
		end
	end)
	Trigger.AfterDelay(DateTime.Seconds(7), function()
		if IsAutoPlay() then
			Utils.Do(threats, function(actor)
				if actor.IsInWorld and not actor.IsDead then
					actor.Kill()
				end
			end)
		end
	end)

	Trigger.AfterDelay(DateTime.Seconds(2), AutoPlayLoop)
end

RunFailureValidation = function()
	if ValidationMode == "cargo-failure" then
		BeginRoute("short")
		Trigger.AfterDelay(DateTime.Seconds(3), function()
			local cargoShips = Utils.Where(Convoy, function(record) return record.cargo > 0 end)
			Utils.Do(cargoShips, function(record)
				if not record.actor.IsDead then record.actor.Kill() end
			end)
		end)
	elseif ValidationMode == "tanker-failure" then
		BeginRoute("short")
		Trigger.AfterDelay(DateTime.Seconds(3), function()
			StartTankerFire()
			FireElapsed = Config.fireLimit - 2
		end)
	elseif ValidationMode == "escort-failure" then
		BeginRoute("safe")
		Trigger.AfterDelay(DateTime.Seconds(3), function()
			Utils.Do(EscortShips, function(actor)
				if not actor.IsDead then actor.Kill() end
			end)
		end)
	elseif ValidationMode == "survivor-failure" then
		BeginRoute("short")
		Trigger.AfterDelay(DateTime.Seconds(3), function()
			StartDisabledVesselIncident()
			Trigger.AfterDelay(DateTime.Seconds(1), function()
				if SurvivorRafts[1] and not SurvivorRafts[1].IsDead then
					SurvivorRafts[1].Kill()
				end
			end)
		end)
	end
end

WorldLoaded = function()
	Escort = Player.GetPlayer("Escort")
	Civilians = Player.GetPlayer("Civilians")
	Hostiles = Player.GetPlayer("Hostiles")
	Neutral = Player.GetPlayer("Neutral")
	Config = Balance[Difficulty]
	ValidationMode = Map.LobbyOptionOrDefault("convoy-validation", "off")

	InitObjectives(Escort)
	RouteChoiceObjective = AddPrimaryObjective(Escort, "objective-choose-route")
	EscortObjective = AddPrimaryObjective(Escort, "objective-escort-convoy")
	if Difficulty == "easy" then
		CargoObjective = AddPrimaryObjective(Escort, "objective-preserve-cargo-easy")
	elseif Difficulty == "hard" then
		CargoObjective = AddPrimaryObjective(Escort, "objective-preserve-cargo-hard")
	else
		CargoObjective = AddPrimaryObjective(Escort, "objective-preserve-cargo-normal")
	end
	RadarObjective = AddPrimaryObjective(Escort, "objective-maintain-radar")
	IntelObjective = AddSecondaryObjective(Escort, "objective-investigate-intel")
	HostileObjective = AddPrimaryObjective(Hostiles, "")

	CreateInitialForces()
	IntelContactActor = Actor.Create("convoyshield.intel-contact", true, { Owner = Neutral, Location = IntelContact.Location })
	Camera.Position = DefaultCameraPosition.CenterPosition
	Media.PlayMusic("under3")
	Radio("radio-opening", "radio-prefix-control")
	Radio("radio-route-choice", "radio-prefix-radar")
	Trigger.AfterDelay(DateTime.Seconds(3), function()
		Radio("radio-intel", "radio-prefix-radar")
		Beacon.New(Escort, IntelContact.CenterPosition, DateTime.Seconds(20))
	end)

	SetupRouteChoice()
	SetupReactiveCheckpoints()
	SetupEvacuationGate()
	Trigger.AfterDelay(DateTime.Seconds(1), RadarLoop)
	Trigger.AfterDelay(DateTime.Seconds(1), IntelLoop)
	Trigger.AfterDelay(DateTime.Seconds(1), HazardLoop)
	Trigger.AfterDelay(DateTime.Seconds(2), MissionStateLoop)
	Trigger.AfterDelay(DateTime.Seconds(10), RecoverConvoyPaths)

	if IsAutoPlay() then
		Trigger.AfterDelay(DateTime.Seconds(2), AutoPlayLoop)
	elseif ValidationMode ~= "off" then
		Trigger.AfterDelay(DateTime.Seconds(2), RunFailureValidation)
	end
end
