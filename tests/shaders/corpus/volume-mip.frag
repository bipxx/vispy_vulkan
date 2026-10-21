vec4 null_transform_map(vec4 pos) {return pos;}

vec4 transform_map_chain(vec4 pos) {
    vec4 result_1 = null_transform_map(pos);
    return result_1;
}

vec4 null_transform_map_1(vec4 pos) {return pos;}

vec4 transform_map_chain_1(vec4 pos) {
    vec4 result_1 = null_transform_map_1(pos);
    return result_1;
}

vec4 transform_map_chain_6(vec4 pos) {
    vec4 result_1 = transform_map_chain(pos);
    vec4 result_2 = transform_map_chain_1(result_1);
    return result_2;
}


vec4 grays(float t) {
    // Map NaN to bad_color
    if (!(t <= 0.0 || 0.0 <= t)) {
        return vec4(0.000, 0.000, 0.000, 0.000);
    }
    return vec4(t, t, t, 1.0);
}


vec4 transform_map_chain_7(vec4 pos) {
    vec4 result_1 = transform_map_chain(pos);
    return result_1;
}


float clip_planes(vec3 loc, vec3 vol_shape) {
    vec3 loc_transf = transform_map_chain_7(vec4(loc * vol_shape, 1)).xyz;
    float distance_from_clip = 3.4e38; // max float
    ;
    return distance_from_clip;
}


uniform sampler3D u_texture;

vec4 texture_lookup(vec3 texcoord) {
    // no need to discard out of bounds, already checked during raycasting
    return texture3D(u_texture, texcoord);
}


// uniforms
uniform sampler3D u_volumetex;
uniform vec3 u_shape;
uniform vec2 clim;
uniform float gamma;
uniform float u_threshold;
uniform float u_attenuation;
uniform float u_relative_step_size;
uniform float u_mip_cutoff;
uniform float u_minip_cutoff;
uniform int u_rgb_mode;

//varyings
varying vec3 v_position;
varying vec4 v_nearpos;
varying vec4 v_farpos;

// uniforms for lighting. Hard coded until we figure out how to do lights
const vec4 u_ambient = vec4(0.2, 0.2, 0.2, 1.0);
const vec4 u_diffuse = vec4(0.8, 0.2, 0.2, 1.0);
const vec4 u_specular = vec4(1.0, 1.0, 1.0, 1.0);
const float u_shininess = 40.0;

// uniforms for plane definition. Defined in data coordinates.
uniform vec3 u_plane_normal;
uniform vec3 u_plane_position;
uniform float u_plane_thickness;

//varying vec3 lightDirs[1];

// global holding view direction in local coordinates
vec3 view_ray;

float rand(vec2 co)
{
    // Create a pseudo-random number between 0 and 1.
    // http://stackoverflow.com/questions/4200224
    return fract(sin(dot(co.xy ,vec2(12.9898, 78.233))) * 43758.5453);
}

float colorToVal(vec4 color)
{
    if (u_rgb_mode == 1)
        // perceptual luminance, a good approach to transform rgb into a single
        // value for things like gradient calculations in isosurface
        return dot(color.rgb, vec3(0.2126, 0.7152, 0.0722)) * color.a;
    return color.r;
}

vec4 applyColormap(vec4 color) {
    // clim and gamma are applied identically in both modes: per channel for rgb
    // data, and to the single (red) channel for scalar data.
    color.rgb = clamp(color.rgb, min(clim.x, clim.y), max(clim.x, clim.y));
    color.rgb = (color.rgb - clim.x) / (clim.y - clim.x);
    color.rgb = pow(color.rgb, vec3(gamma));
    if (u_rgb_mode == 1) {
        // no colormapping, the rgb values are used directly
        return color;
    }
    return grays(color.r);
}


vec4 calculateColor(vec4 betterColor, vec3 loc, vec3 step)
{   
    // Calculate color by incorporating lighting
    vec4 color1;
    vec4 color2;

    // View direction
    vec3 V = normalize(view_ray);

    // calculate normal vector from gradient
    vec3 N; // normal
    color1 = texture_lookup(loc+vec3(-step[0],0.0,0.0) );
    color2 = texture_lookup(loc+vec3(step[0],0.0,0.0) );
    N[0] = colorToVal(color1) - colorToVal(color2);
    betterColor = max(max(color1, color2),betterColor);
    color1 = texture_lookup(loc+vec3(0.0,-step[1],0.0) );
    color2 = texture_lookup(loc+vec3(0.0,step[1],0.0) );
    N[1] = colorToVal(color1) - colorToVal(color2);
    betterColor = max(max(color1, color2),betterColor);
    color1 = texture_lookup(loc+vec3(0.0,0.0,-step[2]) );
    color2 = texture_lookup(loc+vec3(0.0,0.0,step[2]) );
    N[2] = colorToVal(color1) - colorToVal(color2);
    betterColor = max(max(color1, color2),betterColor);
    float gm = length(N); // gradient magnitude
    N = normalize(N);

    // Flip normal so it points towards viewer
    float Nselect = float(dot(N,V) > 0.0);
    N = (2.0*Nselect - 1.0) * N;  // ==  Nselect * N - (1.0-Nselect)*N;

    // Get color of the texture (albeido)
    color1 = betterColor;
    color2 = color1;
    // todo: parametrise color1_to_color2

    // Init colors
    vec4 ambient_color = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 diffuse_color = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 specular_color = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 final_color;

    // todo: allow multiple light, define lights on viewvox or subscene
    int nlights = 1; 
    for (int i=0; i<nlights; i++)
    { 
        // Get light direction (make sure to prevent zero devision)
        vec3 L = normalize(view_ray);  //lightDirs[i]; 
        float lightEnabled = float( length(L) > 0.0 );
        L = normalize(L+(1.0-lightEnabled));

        // Calculate lighting properties
        float lambertTerm = clamp( dot(N,L), 0.0, 1.0 );
        vec3 H = normalize(L+V); // Halfway vector
        float specularTerm = pow( max(dot(H,N),0.0), u_shininess);

        // Calculate mask
        float mask1 = lightEnabled;

        // Calculate colors
        ambient_color +=  mask1 * u_ambient;  // * gl_LightSource[i].ambient;
        diffuse_color +=  mask1 * lambertTerm;
        specular_color += mask1 * specularTerm * u_specular;
    }

    // Calculate final color by componing different components
    final_color = color2 * ( ambient_color + diffuse_color) + specular_color;
    final_color.a = color2.a;

    // Done
    return final_color;
}


vec3 intersectLinePlane(vec3 linePosition, 
                        vec3 lineVector, 
                        vec3 planePosition, 
                        vec3 planeNormal) {
    // function to find the intersection between a line and a plane
    // line is defined by position and vector
    // plane is defined by position and normal vector
    // https://en.wikipedia.org/wiki/Line%E2%80%93plane_intersection

    // find scale factor for line vector
    float scaleFactor = dot(planePosition - linePosition, planeNormal) / 
                        dot(lineVector, planeNormal);

    // calculate intersection
    return linePosition + ( scaleFactor * lineVector );
}

// for some reason, this has to be the last function in order for the
// filters to be inserted in the correct place...

void main() {
    vec3 farpos = v_farpos.xyz / v_farpos.w;
    vec3 nearpos = v_nearpos.xyz / v_nearpos.w;

    // Calculate unit vector pointing in the view direction through this
    // fragment.
    view_ray = normalize(farpos.xyz - nearpos.xyz);

    // Variables to keep track of where to set the frag depth.
    // frag_depth_point is in data coordinates.
    vec3 frag_depth_point;

    // Set up the ray casting
    // This snippet must define three variables:
    // vec3 start_loc - the starting location of the ray in texture coordinates
    // vec3 step - the step vector in texture coordinates
    // int nsteps - the number of steps to make through the texture
    
    
    // Compute the distance to the front surface or near clipping plane
    float distance = dot(nearpos-v_position, view_ray);
    distance = max(distance, min((-0.5 - v_position.x) / view_ray.x,
                            (u_shape.x - 0.5 - v_position.x) / view_ray.x));
    distance = max(distance, min((-0.5 - v_position.y) / view_ray.y,
                            (u_shape.y - 0.5 - v_position.y) / view_ray.y));
    distance = max(distance, min((-0.5 - v_position.z) / view_ray.z,
                            (u_shape.z - 0.5 - v_position.z) / view_ray.z));

    // Now we have the starting position on the front surface
    vec3 front = v_position + view_ray * distance;

    // Decide how many steps to take
    int nsteps = int(-distance / u_relative_step_size + 0.5);
    float f_nsteps = float(nsteps);
    if( nsteps < 1 )
        discard;

    // Get starting location and step vector in texture coordinates
    vec3 step = ((v_position - front) / u_shape) / f_nsteps;
    // 0.5 offset needed to get back to correct texture coordinates (vispy#2239)
    vec3 start_loc = (front + 0.5) / u_shape;

    // set frag depth to the cube face; this can be overridden by projection snippets
    frag_depth_point = front;


    // For testing: show the number of steps. This helps to establish
    // whether the rays are correctly oriented
    //gl_FragColor = vec4(0.0, f_nsteps / 3.0 / u_shape.x, 1.0, 1.0);
    //return;

    
        float maxval = u_mip_cutoff; // The maximum encountered value
        int maxi = -1;  // Where the maximum value was encountered
        

    // This outer loop seems necessary on some systems for large
    // datasets. Ugly, but it works ...
    vec3 loc = start_loc;
    int iter = 0;

    // keep track if the texture is ever sampled; if not, fragment will be discarded
    // this allows us to discard fragments that only traverse clipped parts of the texture
    bool texture_sampled = false;

    while (iter < nsteps) {
        for (iter=iter; iter<nsteps; iter++)
        {
            // Only sample volume if loc is not clipped by clipping planes
            float distance_from_clip = clip_planes(loc, u_shape);
            if (distance_from_clip >= 0)
            {
                // Get sample color
                vec4 color = texture_lookup(loc);
                float val = colorToVal(color);
                texture_sampled = true;

                
        if ( val > maxval ) {
            maxval = val;
            maxi = iter;
            if ( maxval >= clim.y ) {
                // stop if no chance of finding a higher maxval
                iter = nsteps;
            }
        }
        
            }
            // Advance location deeper into the volume
            loc += step;
        }
    }

    if (!texture_sampled)
        discard;

    
        // Refine search for max value, but only if anything was found
        if ( maxi > -1 ) {
            // Calculate starting location of ray for sampling
            vec3 start_loc_refine = start_loc + step * (float(maxi) - 0.5);
            loc = start_loc_refine;

            // Variables to keep track of current value and where max was encountered
            vec3 max_loc_tex = start_loc_refine;

            vec3 small_step = step * 0.1;
            // the coarse pass only kept the max *value*, so re-sample its
            // location to get the color it belongs to; the refinement below
            // replaces it only if it finds something brighter
            vec4 maxcolor = texture_lookup(start_loc + step * float(maxi));
            for (int i=0; i<10; i++) {
                vec4 scolor = texture_lookup(loc);
                float val = colorToVal(scolor);
                if ( val > maxval) {
                    maxval = val;
                    maxcolor = scolor;
                    max_loc_tex = start_loc_refine + (small_step * i);
                }
                loc += small_step;
            }
            frag_depth_point = max_loc_tex * u_shape;
            gl_FragColor = applyColormap(maxcolor);
        } else {
            discard;
        }
        

    // set frag depth
    vec4 frag_depth_vector = vec4(frag_depth_point, 1);
    vec4 iproj = transform_map_chain_6(frag_depth_vector);
    iproj.z /= iproj.w;
    gl_FragDepth = (iproj.z+1.0)/2.0;
}

