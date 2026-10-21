uniform sampler2D u_texture_1;

vec4 texture_lookup(vec2 texcoord) {
    if(texcoord.x < 0.0 || texcoord.x > 1.0 ||
    texcoord.y < 0.0 || texcoord.y > 1.0) {
        discard;
    }
    return texture2D(u_texture_1, texcoord);
}

vec4 pass(vec4 color) { return color; }

uniform vec2 u_clim;

vec4 apply_clim(vec4 color) {
    // Handle NaN values (clamp them to the minimum value)
    // http://stackoverflow.com/questions/11810158/how-to-deal-with-nan-or-inf-in-opengl-es-2-0-shaders
    color.r = !(color.r <= 0.0 || 0.0 <= color.r) ? min(u_clim.x, u_clim.y) : color.r;
    color.g = !(color.g <= 0.0 || 0.0 <= color.g) ? min(u_clim.x, u_clim.y) : color.g;
    color.b = !(color.b <= 0.0 || 0.0 <= color.b) ? min(u_clim.x, u_clim.y) : color.b;
    color.a = !(color.a <= 0.0 || 0.0 <= color.a) ? 0 : color.a;
    color.rgb = clamp(color.rgb, min(u_clim.x, u_clim.y), max(u_clim.x, u_clim.y));
    color.rgb = (color.rgb - u_clim.x) / (u_clim.y - u_clim.x);
    return max(color, 0.0);
}


uniform float u_gamma;

vec4 apply_gamma(vec4 color) {
    color.rgb = pow(color.rgb, vec3(u_gamma));
    return color;
}


vec4 chain(vec4 color) {
    vec4 result_1 = pass(color);
    vec4 result_2 = apply_clim(result_1);
    vec4 result_3 = apply_gamma(result_2);
    return result_3;
}

vec4 null_transform_map(vec4 pos) {return pos;}


uniform vec2 image_size;
uniform int method;  // 0=subdivide, 1=impostor
uniform sampler2D u_texture;
varying vec2 v_texcoord;

vec4 map_local_to_tex(vec4 x) {
    // Cast ray from 3D viewport to surface of image
    // (if null_transform_map does not affect z values, then this
    // can be optimized as simply null_transform_map.map(x) )
    vec4 p1 = null_transform_map(x);
    vec4 p2 = null_transform_map(x + vec4(0, 0, 0.5, 0));
    p1 /= p1.w;
    p2 /= p2.w;
    vec4 d = p2 - p1;
    float f = p2.z / d.z;
    vec4 p3 = p2 - d * f;

    // finally map local to texture coords
    return vec4(p3.xy / image_size, 0, 1);
}


void main()
{
    vec2 texcoord;
    if( method == 0 ) {
        texcoord = v_texcoord;
    }
    else {
        // vertex shader outputs clip coordinates;
        // fragment shader maps to texture coordinates
        texcoord = map_local_to_tex(vec4(v_texcoord, 0, 1)).xy;
    }

    gl_FragColor = chain(texture_lookup(texcoord));
}

