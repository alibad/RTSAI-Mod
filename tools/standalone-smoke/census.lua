-- Standalone smoke test (tools/standalone-smoke.py --lua census.lua): logs every actor type in the world (all owners,
-- buildings, units, effects actors, husks) every 5 s to lua.log as CENSUS-ALL|tick|type:count,... For finding which
-- actors a game really puts on screen, e.g. to check them against the placeholder list.
WorldLoaded = function()
  local function census()
    local counts = {}
    for _, a in ipairs(Map.ActorsInWorld) do
      counts[a.Type] = (counts[a.Type] or 0) + 1
    end
    local parts = {}
    for t, n in pairs(counts) do parts[#parts + 1] = t .. ":" .. n end
    table.sort(parts)
    print("CENSUS-ALL|" .. DateTime.GameTime .. "|" .. table.concat(parts, ","))
    Trigger.AfterDelay(DateTime.Seconds(5), census)
  end
  Trigger.AfterDelay(DateTime.Seconds(1), census)
end
