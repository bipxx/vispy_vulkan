#version 330
flat in uvec2 v_ids;
smooth in vec4 v_values;
flat in float v_tail;
out vec4 color;
void main(){float value=float(v_ids.x)+float(v_values.x)+float(v_tail); color=vec4(value*.00001,0.,0.,1.);}
