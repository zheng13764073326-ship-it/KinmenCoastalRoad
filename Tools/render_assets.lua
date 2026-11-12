-- Generated for this project. REAPER renders all seven asset projects at 48 kHz / 24 bit / stereo.
local _, script = reaper.get_action_context()
local root = script:gsub(string.char(92),"/"):match("^(.*)/Tools/[^/]+$")
local names = {"AMB_Kinmen_Roadside_Wind_Loop","SFX_Vehicle_Pass_01","SFX_Vehicle_Pass_02","SFX_Vehicle_Pass_03","SFX_Vehicle_Pass_04","SFX_Bird_Sparse_01","SFX_Bird_Sparse_02"}
for _, name in ipairs(names) do
  reaper.Main_openProject(root .. "/Reaper/AssetProjects/" .. name .. ".rpp")
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", reaper.GetProjectLength(0), true)
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_TAILFLAG", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_DITHER", 0, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", root .. "/Assets/Audio", true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", name, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "ZXZhdxgAAA==", true)
  reaper.Main_SaveProject(0, false)
  reaper.Main_OnCommand(41824, 0)
  reaper.Main_SaveProject(0, false)
end
local f=io.open(root.."/Docs/reaper_render_complete.txt","w")
if f then f:write("REAPER render automation reached completion. Independently verify WAV headers and file timestamps.\n"); f:close() end
