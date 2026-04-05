#version 130

// Standard Panda3D built-in uniforms
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;

// We only need diffuse, position, shadowMap and shadowViewMatrix from the
// light source.  Panda3D matches struct fields by name so a partial struct
// is fine — omit anything you don't use.
struct p3d_LightSourceParameters {
    vec4 diffuse;
    vec4 position;          // w=0 means directional; xyz = direction-to-light in view space
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;  // view-space → shadow-map texture space
};
uniform p3d_LightSourceParameters p3d_LightSource[1];

// Per-vertex inputs
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 p3d_Color;

// Outputs to fragment shader
out vec4 vColor;
out vec3 vNormal;       // view-space normal
out vec4 vShadowCoord;  // homogeneous shadow-map coordinate

void main() {
    vec4 eyePos     = p3d_ModelViewMatrix * p3d_Vertex;
    gl_Position     = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    vColor          = p3d_Color;
    vNormal         = normalize(p3d_NormalMatrix * p3d_Normal);
    vShadowCoord    = p3d_LightSource[0].shadowViewMatrix * eyePos;
}
