--[[
   Original reusable mission helpers for OpenRA AI.
   Patterns are informed by public GPL OpenRA campaigns, but mission text,
   characters, timing, geography, and story content remain original.
]]

ExperienceObjectives = { }

--- Add a primary or secondary objective without duplicating the branch at each call site.
---@param player player
---@param objectiveType string "primary" or "secondary"
---@param fluentKey string
---@return integer
ExperienceObjectives.Add = function(player, objectiveType, fluentKey)
	if objectiveType == "secondary" then
		return player.AddSecondaryObjective(fluentKey)
	end

	return player.AddPrimaryObjective(fluentKey)
end

--- Complete an objective only when it remains active.
---@param player player
---@param objective integer
ExperienceObjectives.Complete = function(player, objective)
	if objective and not player.IsObjectiveCompleted(objective) then
		player.MarkCompletedObjective(objective)
	end
end

--- Fail an objective only when it remains active.
---@param player player
---@param objective integer
ExperienceObjectives.Fail = function(player, objective)
	if objective and not player.IsObjectiveCompleted(objective) then
		player.MarkFailedObjective(objective)
	end
end

--- Schedule an original mission beat in whole seconds.
---@param seconds integer
---@param callback function
ExperienceObjectives.AfterSeconds = function(seconds, callback)
	Trigger.AfterDelay(DateTime.Seconds(seconds), callback)
end

--- Return the living, in-world members of a mission group.
---@param actors actor[]
---@return actor[]
ExperienceObjectives.Living = function(actors)
	return Utils.Where(actors, function(actor)
		return actor and not actor.IsDead and actor.IsInWorld
	end)
end

--- Test whether an actor is within a cell radius of an actor or waypoint.
---@param actor actor
---@param target actor
---@param radius integer
---@return boolean
ExperienceObjectives.IsNear = function(actor, target, radius)
	if not actor or actor.IsDead or not actor.IsInWorld or not target then
		return false
	end

	return Utils.Any(Map.ActorsInCircle(target.CenterPosition, WDist.FromCells(radius)), function(candidate)
		return candidate == actor
	end)
end

--- Move a convoy in route order, preserving authored waypoints and tolerance.
---@param actors actor[]
---@param route actor[]
---@param tolerance integer
ExperienceObjectives.FollowRoute = function(actors, route, tolerance)
	Utils.Do(ExperienceObjectives.Living(actors), function(actor)
		actor.Stop()
		Utils.Do(route, function(waypoint)
			actor.Move(waypoint.Location, tolerance or 1)
		end)
	end)
end

--- Scale a value by the standard campaign difficulty vocabulary.
---@param easy integer
---@param normal integer
---@param hard integer
---@return integer
ExperienceObjectives.ForDifficulty = function(easy, normal, hard)
	if Difficulty == "easy" then
		return easy
	elseif Difficulty == "hard" then
		return hard
	end

	return normal
end
