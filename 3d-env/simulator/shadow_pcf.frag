#version 130

struct p3d_LightSourceParameters {
    vec4 diffuse;
    vec4 position;
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;
};
struct p3d_LightModelParameters {
    vec4 ambient;   // combined contribution from all AmbientLight nodes
};

uniform p3d_LightSourceParameters p3d_LightSource[1];
uniform p3d_LightModelParameters  p3d_LightModel;

in vec4 vColor;
in vec3 vNormal;
in vec4 vShadowCoord;

out vec4 fragColor;

// ------------------------------------------------------------
// 8-sample Poisson disk — well-spread, no obvious pattern
// ------------------------------------------------------------
const vec2 disk[8] = vec2[](
    vec2(-0.94201624, -0.39906216),
    vec2( 0.94558609, -0.76890725),
    vec2(-0.09418410, -0.92938870),
    vec2( 0.34495938,  0.29387760),
    vec2(-0.91588581,  0.45771432),
    vec2(-0.81544232, -0.87912464),
    vec2(-0.38277543,  0.27676845),
    vec2( 0.97484398,  0.75648379)
);

// ------------------------------------------------------------
// PCF shadow sampling
//   blurRadius — spread of the Poisson disk in texture space.
//   Blur radius is expressed in shadow-map UV space.
//   Keep it small enough to avoid a smeared look, but wide enough to break up
//   visible texel structure on large, flat terrain patches.
// ------------------------------------------------------------
float sampleShadow(vec4 coord, float blurRadius, float depthBias) {
    // Behind light / invalid projection: don't darken.
    if (coord.w <= 0.0) {
        return 1.0;
    }

    // Perspective divide → [0,1] shadow-map texture space
    vec3 sc = coord.xyz / coord.w;

    // Outside the shadow map = fully lit.
    if (sc.x <= 0.0 || sc.x >= 1.0 ||
        sc.y <= 0.0 || sc.y >= 1.0 ||
        sc.z <= 0.0 || sc.z >= 1.0) {
        return 1.0;
    }

    float lit = 0.0;
    for (int i = 0; i < 8; i++) {
        // Offset only s,t — keep depth (sc.z) fixed for correct comparison
        lit += texture(p3d_LightSource[0].shadowMap,
                       sc + vec3(disk[i] * blurRadius, -depthBias));
    }
    float shadow = lit / 8.0;

    // Fade to fully lit near map edges so the moving shadow-camera window
    // never appears as a visible dark rectangle on terrain.
    float edge = min(min(sc.x, 1.0 - sc.x), min(sc.y, 1.0 - sc.y));
    float edgeFade = smoothstep(0.0, 0.12, edge);
    return mix(1.0, shadow, edgeFade);
}

void main() {
    vec3  N        = normalize(vNormal);
    vec3  L        = normalize(p3d_LightSource[0].position.xyz); // toward sun, view-space
    float diff     = max(dot(N, L), 0.0);
    float bias     = max(0.0015, 0.0035 * (1.0 - diff));
    float shadow   = sampleShadow(vShadowCoord, 0.0015, bias);

    vec4 ambient   = p3d_LightModel.ambient              * vColor;
    vec4 diffuse   = p3d_LightSource[0].diffuse * diff * shadow * vColor;

    fragColor   = clamp(ambient + diffuse, 0.0, 1.0);
    fragColor.a = vColor.a;
}
