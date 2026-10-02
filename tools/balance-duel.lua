--[[
Unit-value duels, installed into a disposable copy of the blank map by tools/balance-duel.py.

Each duel spawns two groups of (about) equal build value for the non-playable players DuelA and
DuelB, orders both to attack-move through each other, and records what is left of each side when one
side is gone or the duel times out. No bot is involved: this measures what the units are worth, not
how well a bot uses them. Side A alternates between the west and east start lines per replicate.

Output: one "DUEL|<id>|<tick>|<a value left>|<b value left>|<a alive>|<b alive>|<a value>|<b value>"
line per duel in lua.log (value left = cost x remaining health fraction), then "DUELS|done".
]]

local Duels = { __DUELS__ }
local Timeout = __TIMEOUT__
local Budget = __BUDGET__
local CheckInterval = 25
DEBUG = false
-- Positions are map (u, v) coordinates (MPos); Cell converts them to the isometric CPos.
local Center = { u = 64, v = 72 }
local Gap = 12

local A, B
local CostCache = { }

local function CostOf(actorType)
	local cached = CostCache[actorType]
	if cached == nil then
		local ok, value = pcall(function() return Actor.Cost(actorType) end)
		cached = ok and value or 0
		CostCache[actorType] = cached
	end
	return cached
end

local function Cell(u, v)
	local y = math.floor(v / 2) - u
	return CPos.New(v - y, y)
end

local function Spawn(player, actorType, count, u, level)
	local units = { }
	local outward = u < Center.u and -1 or 1
	for i = 0, count - 1 do
		local column = math.floor(i / 8)
		local cell = Cell(u + column * outward, Center.v - 8 + 2 * (i % 8))
		-- Face the enemy line: spawning with the default facing made one side turn around first.
		local facing = outward < 0 and Angle.East or Angle.West
		local actor = Actor.Create(actorType, true, { Owner = player, Location = cell, Facing = facing })
		if level > 0 and actor.HasProperty("GiveLevels") then
			actor.GiveLevels(level, true)
		end
		units[#units + 1] = actor
	end
	return units
end

local function Remaining(units)
	local value, alive = 0, 0
	for _, actor in ipairs(units) do
		if not actor.IsDead then
			alive = alive + 1
			value = value + math.floor(CostOf(actor.Type) * actor.Health / actor.MaxHealth)
		end
	end
	return value, alive
end

local function Clear()
	for _, player in ipairs({ A, B }) do
		for _, actor in ipairs(player.GetActors()) do
			-- GetActors includes the player actor itself; never destroy that.
			if actor.Type ~= "player" and not actor.IsDead and actor.IsInWorld then
				actor.Destroy()
			end
		end
	end
end

local RunDuel

local function Finish()
	print("DUELS|done")
	local local_player = Player.GetPlayer("Multi0")
	local objective = local_player.AddPrimaryObjective("Duels finished")
	local_player.MarkFailedObjective(objective)
end

RunDuel = function(index)
	local duel = Duels[index]
	if duel == nil then
		Finish()
		return
	end

	-- Successive duels alternate between two separate fields, so nothing from the last one is near.
	Center.v = index % 2 == 0 and 104 or 40
	local west, east = Center.u - Gap, Center.u + Gap
	-- Side A starts west in even replicates and east in odd ones, so start-line effects cancel per pair.
	local ax, bx = west, east
	if not duel.west then
		ax, bx = east, west
	end

	-- Equal build value: the unit counts near the budget whose total values differ least.
	local ca, cb = CostOf(duel.a), CostOf(duel.b)
	local na, nb, best = 1, 1, nil
	for n = math.max(1, math.floor(Budget * 0.75 / ca)), math.max(1, math.floor(Budget * 1.5 / ca)) do
		local m = math.max(1, math.floor(n * ca / cb + 0.5))
		local diff = math.abs(n * ca - m * cb) / (n * ca)
		if best == nil or diff < best - 0.001 then
			na, nb, best = n, m, diff
		end
	end
	local a = Spawn(A, duel.a, na, ax, duel.level)
	local b = Spawn(B, duel.b, nb, bx, duel.level)
	local aValue, bValue = CostOf(duel.a) * na, CostOf(duel.b) * nb
	for _, actor in ipairs(a) do
		actor.AttackMove(Cell(bx + math.floor((bx - ax) / 2), Center.v), 2)
	end
	for _, actor in ipairs(b) do
		actor.AttackMove(Cell(ax + math.floor((ax - bx) / 2), Center.v), 2)
	end

	local started = DateTime.GameTime
	local function Check()
		local aLeft, aAlive = Remaining(a)
		local bLeft, bAlive = Remaining(b)
		local elapsed = DateTime.GameTime - started
		if DEBUG and a[1] ~= nil and not a[1].IsDead and b[1] ~= nil and not b[1].IsDead then
			print("DBG|" .. duel.id .. "|" .. elapsed .. "|" .. tostring(a[1].Location) .. "|" .. tostring(b[1].Location) .. "|" .. a[1].Health .. "|" .. b[1].Health .. "|" .. tostring(a[1].Owner.InternalName) .. "|" .. tostring(b[1].Owner.InternalName))
		end
		if aAlive == 0 or bAlive == 0 or elapsed >= Timeout then
			print(table.concat({ "DUEL", duel.id, tostring(elapsed), tostring(aLeft), tostring(bLeft),
				tostring(aAlive), tostring(bAlive), tostring(aValue), tostring(bValue) }, "|"))
			-- Husks appear a few ticks after a death; clear twice so none is left as a target.
			Clear()
			Trigger.AfterDelay(25, Clear)
			Trigger.AfterDelay(75, function() RunDuel(index + 1) end)
			return
		end

		Trigger.AfterDelay(CheckInterval, Check)
	end

	Trigger.AfterDelay(CheckInterval, Check)
end

WorldLoaded = function()
	A = Player.GetPlayer("DuelA")
	B = Player.GetPlayer("DuelB")
	Trigger.AfterDelay(50, function() RunDuel(1) end)
end
