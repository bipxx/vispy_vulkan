#version 330
in vec4 a_position;
flat out uvec2 v_ids;
flat out uint v_visits;
float private_state=0.;
void main() { private_state+=1.; gl_Position=a_position+vec4(float(gl_VertexID)*.125,0.,0.,0.);
v_ids=uvec2(uint(gl_VertexID),uint(gl_InstanceID)); v_visits=uint(private_state); }
