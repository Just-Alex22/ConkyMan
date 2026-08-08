conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'below,sticky,skip_taskbar,skip_pager',

    xinerama_head = 0, alignment = 'top_right', gap_x = 20, gap_y = 25,
    minimum_width = 200, minimum_height = 400,
    use_xft = true, font = 'Fira Sans:size=10',
    default_color = 'F5F5F5',
    color1 = 'FFFFFF',
    color2 = 'B0E0E6',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = false,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}

conky.text = [[
    # Reloj
    ${voffset 10}${font Fira Sans:weight=Normal:size=55}${color1}${time %H}${font}${voffset -20}${offset -10}${font Fira Sans:weight=Normal:size=40}${color2}${time %M}${font}
    # Fecha
    ${voffset 10}${font Fira Sans Medium:size=13}${color}${time %a, %d %b %Y}${font}
    # Saludo dinámico
    ${voffset 5}${font Fira Sans:Italic:size=11}${color2}\
    ${if_match ${utime %H} % 3 == 0}Hi!! ${execi 3600 whoami}${else}\
    ${if_match ${utime %H} % 3 == 1}Aloha ${execi 3600 whoami}${else}\
    What's up ${execi 3600 whoami}${endif}${endif}${font}
    ${voffset 5}${hr 1}
    # Recursos
    ${voffset 5}${font Fira Sans:size=10}${color}CPU: ${goto 55}${color2}${cpu}% ${alignr}${cpugraph 8,70 5B8080 B0E0E6}
    ${color}RAM: ${goto 55}${color2}${memperc}% ${alignr}${memgraph 8,70 5B8080 B0E0E6}
    ${color}SWP: ${goto 55}${color2}${swapperc}% ${alignr}${swapbar 8,70 B0E0E6}
    ${color}DSK: ${goto 55}${color2}${fs_used_perc /}% ${alignr}${diskiograph 8,70 5B8080 B0E0E6}
    ${voffset 10}${hr 1}
    # Música
    ${voffset 5}${color2}${font Fira Sans:Bold:size=9}REPRODUCIENDO:
    ${color}${font Fira Mono:size=9}${scroll 30 5 ${execi 5 playerctl metadata --format '{{ title }}'}}
    ${color2}${font Fira Mono:Italic:size=8}${scroll 30 5 ${execi 5 playerctl metadata --format '{{ artist }}'}}${font}
]]
