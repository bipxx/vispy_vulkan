#version 330
flat in uvec2 v_ids;
flat in ivec2 v_signed;
flat in uvec2 v_unsigned;
smooth in vec4 v_raw;
out vec4 color;
void main(){float value=float(v_ids.x)+float(v_signed.x)+float(v_unsigned.x)+float(v_raw.x); color=vec4(value*.00001,0.,0.,1.);}
