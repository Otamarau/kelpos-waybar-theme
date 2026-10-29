-- Rofi 2.0 cannot detect outside clicks on Wayland itself.
-- Layer and cursor coordinates are both in the global monitor layout.
local function close_rofi_on_outside_click()
    local cursor = hl.get_cursor_pos()
    if not cursor then return end

    local pids = {}
    for _, layer in ipairs(hl.get_layers()) do
        if layer.mapped and layer.namespace == "rofi" then
            if cursor.x >= layer.x and cursor.x < layer.x + layer.w
                and cursor.y >= layer.y and cursor.y < layer.y + layer.h then
                return
            end
            if layer.pid and layer.pid > 0 then
                pids[layer.pid] = true
            end
        end
    end
    for pid in pairs(pids) do
        hl.exec_cmd("kill -TERM " .. string.format("%d", pid))
    end
end
hl.bind("mouse:272", close_rofi_on_outside_click, {
    non_consuming = true,
    ignore_mods = true,
})
