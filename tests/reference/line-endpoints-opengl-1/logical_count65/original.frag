#version 330
flat in uvec2 v_ids;
flat in uint v_visits;
out vec4 color;
void main(){float value=float(v_ids.x)+float(v_visits); color=vec4(value*.00001,0.,0.,1.);}
