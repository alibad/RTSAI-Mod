-- Standalone smoke test, human slot (tools/standalone-smoke.py --lua deploy.lua): deploys the host's MCV so the build
-- palette fills, then logs the host's actors every 20 s to lua.log. No other input is simulated.
WorldLoaded = function()
  local me = Player.GetPlayer("Multi0")
  Trigger.AfterDelay(DateTime.Seconds(2), function()
    for _, a in ipairs(me.GetActors()) do
      if a.Type == "amcv" or a.Type == "smcv" then a.Deploy() end
    end
  end)
  local function census()
    local parts = {}
    for _, a in ipairs(me.GetActors()) do parts[#parts + 1] = a.Type end
    table.sort(parts)
    print("CENSUS|" .. DateTime.GameTime .. "|" .. me.InternalName .. "|" .. me.Faction .. "|" .. #parts .. "|" .. table.concat(parts, ","))
    Trigger.AfterDelay(DateTime.Seconds(20), census)
  end
  Trigger.AfterDelay(DateTime.Seconds(5), census)
end
