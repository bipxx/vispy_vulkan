#version 330
in vec4 a_position; in ivec2 a_signed; in uvec2 a_unsigned;
flat out uvec2 v_ids;
flat out ivec2 v_signed;
flat out uvec2 v_unsigned;
smooth out vec4 v_raw;
void main(){gl_Position=a_position; v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID)); v_signed=a_signed; v_unsigned=a_unsigned; v_raw=a_position;}
