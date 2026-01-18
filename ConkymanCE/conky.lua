conky.config = {
    out_to_wayland = true,
    out_to_x = true,
    
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal', 
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',

    xinerama_head = 0, 
    
    alignment = 'top_right',
    gap_x = 20,
    gap_y = 40,
    minimum_width = 200,
    minimum_height = 300,
    
    use_xft = true,
    font = 'Roboto:size=10',
    default_color = 'F5F5F5',
    color1 = 'E0E0E0', 
    color2 = '8AA34F', 
    
    update_interval = 1.0,
    double_buffer = true,
    draw_shades = false,
    draw_outline = false,
    draw_borders = false,
    draw_graph_borders = true,
    cpu_avg_samples = 2,
    net_avg_samples = 2,
    
    override_utf8_locale = true,
    format_human_readable = true,
}

conky.text = [[
${voffset -20}${font Roboto:weight=Normal:size=85}${color1}${time %H}${font}
${voffset -40}${offset 75}${font Roboto Condensed:weight=Medium:size=80}${color2}${time %M}${font}
${font Roboto Condensed:size=14}${color}${time %a, %d %b %Y}${font}
${font Roboto Condensed:size=12}${color}
Disk: ${color2}${fs_used_perc /}%${color} ${diskiograph 10,20 5B8080 8AA34F}${color}  RAM: ${color2}${memperc}%${color} ${memgraph 10,20 5B8080 8AA34F}${color}
${offset 50}CPU: ${color2}${cpu}%${color} ${cpugraph 10,20 5B8080 8AA34F}${color}
]]
