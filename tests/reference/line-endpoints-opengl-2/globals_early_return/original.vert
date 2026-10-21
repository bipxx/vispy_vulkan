#version 330
in vec4 a_position;
flat out uvec2 v_ids;
smooth out vec4 v_values;
flat out float v_tail;
float private_state=2.;
float seed(float value) { private_state+=1.; return value+float(gl_VertexID%13)+float(gl_InstanceID%7); }
float direct=a_position.x+float(gl_VertexID);
float from_helper=seed(direct);
float conditional=a_position.y>0.?from_helper:-direct;
void main() {
    gl_Position=a_position; v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID));
    v_values=vec4(direct,from_helper,conditional,private_state); v_tail=private_state;
    if(gl_InstanceID%2==1) return;
    private_state+=7.; v_tail=private_state;
}
