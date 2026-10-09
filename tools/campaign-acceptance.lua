-- Controlled fixtures: only the production campaign trait determines outcomes.
local Human
local Neutral
local Started = {}
local ReachActors = {}
local Finished = false
local KeptConvoy
local function Emit(value) print("ACCEPT|" .. value .. "|" .. DateTime.GameTime) end
local function Named(name) return Map.NamedActor(name) end
local function Kill(actor)
    if actor and not actor.IsDead then actor.Kill() end
end
local function Create(kind, location, deployed)
    local init = {Owner = Human, Location = location}
    if deployed then init.DeployState = 2 end
    return Actor.Create(kind, true, init)
end
function WorldLoaded()
    Human = Player.GetPlayer(Mission.slot)
    Neutral = Player.GetPlayer("Neutral")
    Trigger.OnPlayerWon(Human, function() Finished = true; Emit("outcome|won") end)
    Trigger.OnPlayerLost(Human, function() Finished = true; Emit("outcome|lost") end)
    Trigger.OnObjectiveCompleted(Human, function(p, id) Emit("complete|" .. id) end)
    Trigger.OnObjectiveFailed(Human, function(p, id) Emit("failed|" .. id) end)
    Emit("loaded|" .. Mission.id)
    Emit("difficulty|" .. Map.LobbyOptionOrDefault("difficulty", "normal"))
end
function Tick()
    if Finished then return end
    local tick = DateTime.GameTime
    if tick == 10 then
        if Case.wipe then
            for _, actor in ipairs(Human.GetActors()) do
                if actor.HasProperty("Kill") then Kill(actor) end
            end
        elseif Case.kill then Kill(Named(Case.kill)) end
    end
    if tick < 20 then return end
    if Case.fail_at and tick == Case.fail_at then Kill(Named(Mission.protect[1])) end
    -- Remove combat pressure, retaining named objective and protection actors.
    if tick % 100 == 20 then
        local enemy = Player.GetPlayer(Mission.enemy)
        if enemy then
            for _, actor in ipairs(enemy.GetActors()) do
                if actor.HasProperty("Kill") then actor.Owner = Neutral end
            end
        end
    end
    for index, obj in ipairs(Mission.objectives) do
        local ready = true
        for _, prior in ipairs(obj.requires or {}) do
            if not Human.IsObjectiveCompleted(prior) then ready = false end
        end
        if ready and not Started[index] then
            Started[index] = true
            Emit("drive|" .. (index - 1) .. "|" .. obj.kind)
            if obj.kind == "capture" then
                for _, name in ipairs(obj.targets) do
                    local actor = Named(name)
                    if not actor.IsDead then actor.Owner = Human end
                end
            elseif obj.kind == "destroy" then
                for _, name in ipairs(obj.targets) do Kill(Named(name)) end
            elseif obj.kind == "build" then
                local base = Named(Mission.protect[1])
                for i, kind in ipairs(obj.types) do Create(kind, base.Location + CVec.New(i * 4, 4)) end
            elseif obj.kind == "scout" then
                for _, name in ipairs(obj.targets) do Create("e1", Named(name).Location + CVec.New(1, 1)) end
            elseif obj.kind == "reach" then
                local actors = {}
                for i = 1, (Case.reach_limit or obj.count or 1) do
                    local location = Named(obj.via or obj.target).Location + CVec.New(i - 1, 0)
                    actors[#actors + 1] = Create(obj.types[1], location, obj.deploy and not Case.undeployed)
                end
                ReachActors[index] = actors
            elseif obj.kind == "disperse" then
                if Case.exposed then
                    -- MPos surveillance rectangle -> map cell conversion is mode-specific;
                    -- existing exposed start units are retained for this failure fixture.
                else
                    for _, actor in ipairs(Human.GetActors()) do
                        if actor.HasProperty("Move") and not actor.HasProperty("StartBuildingRepairs") then Kill(actor) end
                    end
                end
            end
        end
        if ready and obj.kind == "reach" and obj.via and tick % 100 == 50 then
            for _, actor in ipairs(ReachActors[index] or {}) do
                if not actor.IsDead then actor.Move(Named(obj.target).Location) end
            end
        end
        if ready and Case.convoy == index and not Human.IsObjectiveCompleted(index - 1) and tick % 25 == 0 then
            for _, player in ipairs(Player.GetPlayers(nil)) do
                for _, actor in ipairs(player.GetActors()) do
                    if actor.Type == "sapc" or actor.Type == "lcrf" then
                        if Case.keep_one and not KeptConvoy then KeptConvoy = tostring(actor) end
                        if not Case.keep_one or tostring(actor) ~= KeptConvoy then Kill(actor) end
                    end
                end
            end
        end
    end
    if tick % 1000 == 0 then
        for i = 0, #Mission.objectives - 1 do
            Emit("state|" .. i .. "|" .. tostring(Human.IsObjectiveCompleted(i)) .. "|" .. tostring(Human.IsObjectiveFailed(i)))
        end
    end
end
