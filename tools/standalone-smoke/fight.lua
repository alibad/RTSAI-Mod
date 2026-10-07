-- Standalone smoke test (tools/standalone-smoke.py --lua fight.lua --look X,Y): two small armies meet at one cell
-- and the camera holds there, for screenshots of combat effects (muzzle flashes, explosions, fire, smoke, deaths).
-- Multi0 should be Türkiye and Multi1 Hezbollah (the unit types below are theirs).
WorldLoaded = function()
  local a = Player.GetPlayer("Multi0")
  local b = Player.GetPlayer("Multi1")
  local cx, cy = __LOOK_X__, __LOOK_Y__
  local function put(owner, type, dx, dy)
    local u = Actor.Create(type, true, { Owner = owner, Location = CPos.New(cx + dx, cy + dy) })
    u.AttackMove(CPos.New(cx, cy))
  end
  Trigger.AfterDelay(DateTime.Seconds(2), function()
    Camera.Position = Map.CenterOfCell(CPos.New(cx, cy))
    for i = -2, 2 do
      put(a, "r2bozkir", -5, i * 2)
      put(a, "r2trat", -7, i)
      put(a, "r2trrifle", -6, i)
      put(b, "r2hztechnical", 5, i * 2)
      put(b, "r2hzat", 7, i)
      put(b, "r2hzrifle", 6, i)
    end
    put(b, "htk", 6, 3)
  end)
end
