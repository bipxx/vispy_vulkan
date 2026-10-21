#version 330
in vec4 a_position;
uniform mat4 u_transform; uniform mat3 u_basis; uniform vec2 u_offsets[2];
uniform bool u_flip; uniform uint u_flags;
flat out uvec2 v_ids;
flat out mat3 v_basis;
noperspective out vec2 v_array[2];
flat out ivec2 v_codes[2];
void main() {
    gl_Position=u_transform*a_position; v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID));
    v_basis=u_basis+mat3(float(gl_VertexID)*.5);
    v_array[0]=a_position.xy+u_offsets[0]; v_array[1]=a_position.zw+u_offsets[1];
    v_codes[0]=ivec2(gl_VertexID,gl_InstanceID);
    v_codes[1]=ivec2(u_flip?-gl_VertexID:gl_VertexID,int(u_flags));
}
