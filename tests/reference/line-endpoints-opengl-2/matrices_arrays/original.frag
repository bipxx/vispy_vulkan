#version 330
flat in uvec2 v_ids;
flat in mat3 v_basis;
noperspective in vec2 v_array[2];
flat in ivec2 v_codes[2];
out vec4 color;
void main(){float value=float(v_ids.x)+float(v_basis[0][0])+float(v_array[0].x)+float(v_codes[0].x); color=vec4(value*.00001,0.,0.,1.);}
