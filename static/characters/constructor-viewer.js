/* Static GLB rendering, using the existing Workshop shaders and decoder. */
export class ConstructorViewer {
  constructor(canvas, error) {
    const gl = canvas.getContext('webgl', { antialias: true, preserveDrawingBuffer: true });
    let program = null;
    const $ = () => error;
    function shader(type, source) {
      const result = gl.createShader(type);
      gl.shaderSource(result, source);
      gl.compileShader(result);
      if (!gl.getShaderParameter(result, gl.COMPILE_STATUS))
        throw new Error(gl.getShaderInfoLog(result));
      return result;
    }
    function initializeGL() {
      if (!gl) {
        $('viewer-error').hidden = false;
        $('viewer-error').textContent =
          'WebGL недоступен. Для 3D-превью включи аппаратное ускорение или открой другой браузер.';
        return;
      }
      const vertex = shader(
        gl.VERTEX_SHADER,
        `
    attribute vec3 aPosition; attribute vec3 aNormal; attribute vec3 aColor; attribute vec2 aUV;
    uniform vec3 uCenter; uniform vec4 uRotation; uniform float uScale; uniform float uAspect; uniform float uRadius;
    varying vec3 vColor; varying vec2 vUV;
    vec3 rotate(vec3 p) {
      vec3 q = vec3(uRotation.x*p.x-uRotation.y*p.z,p.y,uRotation.y*p.x+uRotation.x*p.z);
      return vec3(q.x,uRotation.z*q.y+uRotation.w*q.z,-uRotation.w*q.y+uRotation.z*q.z);
    }
    void main() {
      vec3 p=rotate(aPosition-uCenter);
      gl_Position=vec4(p.x*uScale/uAspect,p.y*uScale,-p.z/(uRadius*3.0),1.0);
      float shade=.55+.45*abs(dot(rotate(aNormal),normalize(vec3(-.4,.7,.6))));
      vColor=aColor*shade; vUV=aUV;
    }`,
      );
      const fragment = shader(
        gl.FRAGMENT_SHADER,
        'precision mediump float; varying vec3 vColor; varying vec2 vUV; uniform sampler2D uAlbedo; void main(){gl_FragColor=vec4(vColor*texture2D(uAlbedo,vUV).rgb,1.0);}',
      );
      program = gl.createProgram();
      gl.attachShader(program, vertex);
      gl.attachShader(program, fragment);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS))
        throw new Error(gl.getProgramInfoLog(program));
      gl.useProgram(program);
      gl.enable(gl.DEPTH_TEST);
      gl.clearColor(30 / 255, 30 / 255, 30 / 255, 1);
    }
    function parseGLB(buffer) {
      const view = new DataView(buffer);
      if (
        view.getUint32(0, true) !== 0x46546c67 ||
        view.getUint32(4, true) !== 2 ||
        view.getUint32(8, true) !== buffer.byteLength
      )
        throw new Error('Повреждённый GLB');
      const jsonLength = view.getUint32(12, true);
      const doc = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, jsonLength)));
      const binaryStart = 28 + jsonLength;
      const primitive = doc.meshes[0].primitives[0];
      const result = {
        ends: doc.meshes[0].extras.command_ends,
        ids: doc.meshes[0].extras.command_ids,
      };
      for (const [key, attribute] of [
        ['positions', 'POSITION'],
        ['normals', 'NORMAL'],
        ['colors', 'COLOR_0'],
      ]) {
        const accessor = doc.accessors[primitive.attributes[attribute]],
          bv = doc.bufferViews[accessor.bufferView];
        if (accessor.componentType !== 5126 || accessor.type !== 'VEC3')
          throw new Error('Неподдерживаемый формат GLB');
        result[key] = new Float32Array(
          buffer,
          binaryStart + (bv.byteOffset || 0) + (accessor.byteOffset || 0),
          accessor.count * 3,
        );
        if (key === 'positions') {
          result.center = accessor.min.map((v, i) => (v + accessor.max[i]) / 2);
        }
      }
      if (primitive.attributes.TEXCOORD_0 !== undefined) {
        const accessor = doc.accessors[primitive.attributes.TEXCOORD_0],
          bv = doc.bufferViews[accessor.bufferView];
        if (
          accessor.componentType !== 5126 ||
          accessor.type !== 'VEC2' ||
          accessor.count !== result.positions.length / 3
        )
          throw Error('Некорректные UV материала');
        result.uvs = new Float32Array(
          buffer,
          binaryStart + (bv.byteOffset || 0) + (accessor.byteOffset || 0),
          accessor.count * 2,
        );
        const material = doc.materials[primitive.material || 0],
          index = material.pbrMetallicRoughness?.baseColorTexture?.index;
        if (index !== undefined) {
          const image = doc.images[doc.textures[index].source],
            imageView = doc.bufferViews[image.bufferView];
          result.textureBlob = new Blob(
            [
              new Uint8Array(
                buffer,
                binaryStart + (imageView.byteOffset || 0),
                imageView.byteLength,
              ),
            ],
            { type: image.mimeType },
          );
        }
      } else result.uvs = new Float32Array((result.positions.length / 3) * 2).fill(0.002);
      result.radius = 0;
      for (let i = 0; i < result.positions.length; i += 3)
        result.radius = Math.max(
          result.radius,
          Math.hypot(...result.center.map((v, j) => result.positions[i + j] - v)),
        );
      return result;
    }

    initializeGL();
    this.neutralTexture = gl ? gl.createTexture() : null;
    if (gl) {
      gl.bindTexture(gl.TEXTURE_2D, this.neutralTexture);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGB,
        1,
        1,
        0,
        gl.RGB,
        gl.UNSIGNED_BYTE,
        new Uint8Array([255, 255, 255]),
      );
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    }
    this.loadVersion = 0;
    this.canvas = canvas;
    this.gl = gl;
    this.program = program;
    this.buffers = {};
    this.parts = {};
    this.slot = '';
    this.yaw = 0.65;
    this.pitch = 0.18;
    this.zoom = 1;
    this.parse = parseGLB;
    this.showBones = false;
    this.bonesOverlay = true;
    this.boneBuffers = {};
    let dragging = null;
    canvas.addEventListener('pointerdown', (e) => {
      dragging = [e.clientX, e.clientY];
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      this.yaw += (e.clientX - dragging[0]) * 0.008;
      this.pitch = Math.max(-1.2, Math.min(1.2, this.pitch + (e.clientY - dragging[1]) * 0.008));
      dragging = [e.clientX, e.clientY];
      this.render();
    });
    canvas.addEventListener('pointerup', () => (dragging = null));
    canvas.addEventListener('pointercancel', () => (dragging = null));
    canvas.addEventListener(
      'wheel',
      (e) => {
        e.preventDefault();
        this.zoom = Math.max(0.45, Math.min(2.8, this.zoom * Math.exp(-e.deltaY * 0.001)));
        this.render();
      },
      { passive: false },
    );
    new ResizeObserver(() => this.render()).observe(canvas);
  }
  setBones(bones) {
    if (!this.gl || !bones) return;
    for (const buffer of Object.values(this.boneBuffers)) this.gl.deleteBuffer(buffer);
    this.boneBuffers = {};
    const byId = Object.fromEntries(bones.map((b) => [b.id, b.position])),
      positions = [];
    for (const bone of bones)
      if (bone.parent) {
        positions.push(...byId[bone.parent], ...bone.position);
      }
    this.boneCount = positions.length / 3;
    for (const [field, values] of [
      ['positions', positions],
      ['normals', new Array(positions.length).fill(0)],
      ['colors', new Array(positions.length / 3).fill([1, 0.8, 0.32]).flat()],
    ]) {
      const buffer = this.gl.createBuffer();
      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, buffer);
      this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array(values), this.gl.STATIC_DRAW);
      this.boneBuffers[field] = buffer;
    }
  }
  bindBuffers(buffers) {
    const gl = this.gl;
    for (const [field, name] of [
      ['positions', 'aPosition'],
      ['normals', 'aNormal'],
      ['colors', 'aColor'],
    ]) {
      gl.bindBuffer(gl.ARRAY_BUFFER, buffers[field]);
      const attribute = gl.getAttribLocation(this.program, name);
      gl.enableVertexAttribArray(attribute);
      gl.vertexAttribPointer(attribute, 3, gl.FLOAT, false, 0, 0);
    }
    const uv = gl.getAttribLocation(this.program, 'aUV');
    if (buffers.uvs) {
      gl.bindBuffer(gl.ARRAY_BUFFER, buffers.uvs);
      gl.enableVertexAttribArray(uv);
      gl.vertexAttribPointer(uv, 2, gl.FLOAT, false, 0, 0);
    } else {
      gl.disableVertexAttribArray(uv);
      gl.vertexAttrib2f(uv, 0.002, 0.002);
    }
  }
  cancelPendingLoads() {
    this.loadVersion++;
  }
  async setParts(parts) {
    const version = ++this.loadVersion,
      prepared = {};
    for (const [slot, info] of Object.entries(parts)) {
      if (info.geometry) {
        const data = info.geometry,
          part = { textureFlipY: data.texture_flip_y !== false };
        for (const key of ['positions', 'normals', 'colors', 'uvs'])
          part[key] = new Float32Array(data[key]);
        if (data.texture) {
          const raw = atob(data.texture),
            bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
          part.textureBlob = new Blob([bytes], { type: 'image/png' });
        }
        prepared[slot] = part;
      } else {
        const raw = atob(info.glb),
          bytes = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
        prepared[slot] = this.parse(bytes.buffer);
      }
    }
    const gl = this.gl;
    try {
      await Promise.all(
        Object.values(prepared).map(async (part) => {
          if (!part.textureBlob || !gl) return;
          const bitmap = await createImageBitmap(part.textureBlob, {
            imageOrientation: part.textureFlipY ? 'flipY' : 'none',
          });
          try {
            const tex = gl.createTexture();
            part.texture = tex;
            gl.bindTexture(gl.TEXTURE_2D, tex);
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, bitmap);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          } finally {
            bitmap.close();
          }
        }),
      );
      if (version !== this.loadVersion) {
        for (const part of Object.values(prepared))
          if (part.texture) gl.deleteTexture(part.texture);
        return false;
      }
      for (const part of Object.values(this.parts))
        if (part.texture) gl.deleteTexture(part.texture);
      this.parts = prepared;
      this.combine();
      return true;
    } catch (e) {
      for (const part of Object.values(prepared)) if (part.texture) gl.deleteTexture(part.texture);
      throw e;
    }
  }
  combine() {
    if (!this.gl || !this.program) return;
    const parts = Object.entries(this.parts)
      .filter(([slot]) => !this.slot || slot === this.slot)
      .map(([, p]) => p);
    if (!parts.length) {
      this.mesh = null;
      this.render();
      return;
    }
    const count = parts.reduce((a, p) => a + p.positions.length, 0);
    this.mesh = { count: count / 3 };
    for (const field of ['positions', 'normals', 'colors']) {
      const values = new Float32Array(count);
      let start = 0;
      for (const p of parts) {
        values.set(p[field], start);
        start += p[field].length;
      }
      this.mesh[field] = values;
    }
    const uvs = new Float32Array(this.mesh.count * 2);
    this.mesh.draws = [];
    let offset = 0;
    for (const part of parts) {
      uvs.set(part.uvs, offset * 2);
      this.mesh.draws.push({
        start: offset,
        count: part.positions.length / 3,
        texture: part.texture,
      });
      offset += part.positions.length / 3;
    }
    this.mesh.uvs = uvs;
    const min = [Infinity, Infinity, Infinity],
      max = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < count; i += 3)
      for (let j = 0; j < 3; j++) {
        min[j] = Math.min(min[j], this.mesh.positions[i + j]);
        max[j] = Math.max(max[j], this.mesh.positions[i + j]);
      }
    this.mesh.center = min.map((v, i) => (v + max[i]) / 2);
    this.mesh.radius = Math.hypot(...max.map((v, i) => (v - min[i]) / 2));
    const gl = this.gl;
    gl.useProgram(this.program);
    for (const [field, name] of [
      ['positions', 'aPosition'],
      ['normals', 'aNormal'],
      ['colors', 'aColor'],
    ]) {
      if (!this.buffers[field]) this.buffers[field] = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers[field]);
      gl.bufferData(gl.ARRAY_BUFFER, this.mesh[field], gl.STATIC_DRAW);
      const a = gl.getAttribLocation(this.program, name);
      gl.enableVertexAttribArray(a);
      gl.vertexAttribPointer(a, 3, gl.FLOAT, false, 0, 0);
    }
    if (!this.buffers.uvs) this.buffers.uvs = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.uvs);
    gl.bufferData(gl.ARRAY_BUFFER, this.mesh.uvs, gl.STATIC_DRAW);
    this.render();
  }
  render() {
    const gl = this.gl,
      p = this.program,
      c = this.canvas;
    if (!gl || !p) return;
    const ratio = Math.min(devicePixelRatio || 1, 2),
      w = Math.max(1, Math.round(c.clientWidth * ratio)),
      h = Math.max(1, Math.round(c.clientHeight * ratio));
    if (c.width !== w || c.height !== h) {
      c.width = w;
      c.height = h;
    }
    gl.viewport(0, 0, w, h);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    if (!this.mesh) return;
    gl.uniform3fv(gl.getUniformLocation(p, 'uCenter'), this.mesh.center);
    gl.uniform4f(
      gl.getUniformLocation(p, 'uRotation'),
      Math.cos(this.yaw),
      Math.sin(this.yaw),
      Math.cos(this.pitch),
      Math.sin(this.pitch),
    );
    gl.uniform1f(
      gl.getUniformLocation(p, 'uScale'),
      ((0.88 * this.zoom) / this.mesh.radius) * Math.min(1, w / h),
    );
    gl.uniform1f(gl.getUniformLocation(p, 'uAspect'), w / h);
    gl.uniform1f(gl.getUniformLocation(p, 'uRadius'), this.mesh.radius);
    this.bindBuffers(this.buffers);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(gl.getUniformLocation(p, 'uAlbedo'), 0);
    for (const draw of this.mesh.draws) {
      gl.bindTexture(gl.TEXTURE_2D, draw.texture || this.neutralTexture);
      gl.drawArrays(gl.TRIANGLES, draw.start, draw.count);
    }
    if (this.showBones && this.boneCount) {
      if (this.bonesOverlay) gl.disable(gl.DEPTH_TEST);
      gl.bindTexture(gl.TEXTURE_2D, this.neutralTexture);
      this.bindBuffers(this.boneBuffers);
      gl.drawArrays(gl.LINES, 0, this.boneCount);
      gl.enable(gl.DEPTH_TEST);
    }
  }
  reset(front = false) {
    this.yaw = front ? 0 : 0.65;
    this.pitch = front ? 0 : 0.18;
    this.zoom = 1;
    this.render();
  }
}

// Compatibility for consumers that still address the independent viewer globally.
globalThis.ConstructorViewer = ConstructorViewer;
