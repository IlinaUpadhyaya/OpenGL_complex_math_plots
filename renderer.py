import cmath
import math
import os  #
import sys
import threading
import time

import OpenGL.GL as GL
import cv2
import glfw
from PIL import Image

from text_renderer import *
from transform import translate, rotate, scale, vec, ortho

out = 0
close_auto = False
WIDTH = 1000
HEIGHT = 1000


def compile_shader(shader_file_name, shader_type):
    if not os.path.exists(shader_file_name):
        print("shader file not found: " + shader_file_name)
        sys.exit(1)
    shader_source_code = open(shader_file_name, 'r').read()
    shader = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader, shader_source_code)
    GL.glCompileShader(shader)
    status = GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS)
    shader_source_code = ('%3d: %s' % (i + 1, l) for i, l in enumerate(shader_source_code.splitlines()))
    if not status:
        log = GL.glGetShaderInfoLog(shader).decode('ascii')
        GL.glDeleteShader(shader)
        shader_source_code = '\n'.join(shader_source_code)
        print('Compile failed for %s\n%s\n%s' % (shader_type, log, shader_source_code))
        sys.exit(1)
    return shader


# returns glid which is a sort of a pointer to the shader in the GPU
def create_shader(file_name_vert_shader, file_name_fragment_shader):
    glid = None
    vert = compile_shader(file_name_vert_shader, GL.GL_VERTEX_SHADER)
    frag = compile_shader(file_name_fragment_shader, GL.GL_FRAGMENT_SHADER)
    if vert and frag:
        glid = GL.glCreateProgram()
        GL.glAttachShader(glid, vert)
        GL.glAttachShader(glid, frag)
        GL.glLinkProgram(glid)
        GL.glDeleteShader(vert)
        GL.glDeleteShader(frag)
        status = GL.glGetProgramiv(glid, GL.GL_LINK_STATUS)
        if not status:
            print(GL.glGetProgramInfoLog(glid).decode('ascii'))
            GL.glDeleteProgram(glid)
            sys.exit(1)
    return glid


class Function:

    def __init__(self, shader, n, m, step):
        self.shader = shader
        self.n = n
        self.m = m
        self.step = step
        positions, colors = self.__get_function_vertices()
        t = tuple(positions)
        self.position = np.array(t, 'f')
        vals = [x[2] for x in self.position]
        self.far = max(vals)
        self.near = min(vals)
        self.color = np.array(tuple(colors), 'f')
        self.size = len(self.position)

        # state variables
        self.base_color = [0, 0, 0]
        self.rot_angle_x = 100
        self.rot_angle_y = 0
        self.rot_angle_z = 0

    def __get_function_vertices(self):

        data = []
        cols = []
        for x in range(-self.n, self.n + 1, 1):
            row = []
            col = []
            for y in range(-self.n, self.n + 1, 1):
                z = complex(x / self.step, y / self.step)
                # print (z)
                if self.m == 0:
                    z = cmath.sqrt(z) + cmath.sin(z)
                    self.f = "C(z) = cmath.sqrt(z) + cmath.sin(z)"
                    row.append((x, y, z.real))
                # elif self.m == 1:
                #     z = cmath.sqrt(z) + cmath.tan(z)
                #     self.f = "C(z) = cmath.sqrt(z) + cmath.tan(z)"
                #     row.append((x, y, z.real))
                elif self.m == 1:
                    z = z ** 2
                    self.f = "C(z) = z ** 2"
                    row.append((x, y, z.real))
                elif self.m == 2:
                    z = z ** 3
                    self.f = "C(z) = z ** 3"
                    row.append((x, y, z.real))
                elif self.m == 3:
                    z = z ** 4 / 5
                    self.f = "C(z) = z ** 4 / 5"
                    row.append((x, y, z.real))
                elif self.m == 4:
                    z = z ** (7 / 3)
                    self.f = "C(z) = z ** 7 / 3"
                    row.append((x, y, z.real))
                elif self.m == 5:
                    try:
                        z = 1 / cmath.exp(z) + cmath.sin(z)
                    except:
                        z = complex(0, 0)
                    self.f = "C(z) = 1 / cmath.exp(z) + cmath.sin(z)"
                    row.append((x, y, z.real))
                elif self.m == 6:
                    z = cmath.exp(z)
                    self.f = "C(z) = cmath.exp(z)"
                    row.append((x, y, z.real))
                elif self.m == 7:
                    try:
                        z = 1 / (cmath.exp(z)) ** 1.5
                    except:
                        z = complex(0, 0)
                    self.f = "C(z) =  1 / (cmath.exp(z)) ** 1.5"
                    row.append((x, y, z.real))
                try:
                    a = abs(1 / abs(z.imag))
                except:
                    a = 0
                if a > 1:
                    a = 1
                col.append((a ** .2, a ** .3, a ** .1))
                if self.m == 8:
                    row.append((x, y, x ** 2 + y ** 2))
                    col.append((1, 1, 0))
                elif self.m == 9:
                    try:
                        row.append((x, y, 1 / math.sin(1 / x) + (1 / y) ** 2))
                        col.append((1, 1, 0))
                    except:
                        row.append((x, y, 0))
                        col.append((1, 1, 0))
                elif self.m == 10:
                    try:
                        row.append((x, y, -10 + math.cos(1 / x ** 2) + 1 / math.tan(1 / x ** 2)))
                        col.append((1, 1, 0))
                    except:
                        row.append((x, y, 0))
                        col.append((1, 1, 0))

            data.append(row)
            cols.append(col)

        triangles = []
        colors = []
        x = 0
        y = 0
        for x in range(2 * self.n):
            for y in range(2 * self.n):
                l_1 = [data[x][y], data[x + 1][y], data[x + 1][y], data[x + 1][y + 1], data[x + 1][y + 1], data[x][y],
                       data[x][y], data[x][y + 1], data[x + 1][y + 1], data[x][y + 1]]
                triangles.extend(l_1)
                colors.extend(
                    [cols[x][y], cols[x + 1][y], cols[x + 1][y], cols[x + 1][y + 1], cols[x + 1][y + 1], cols[x][y],
                     cols[x][y], cols[x][y + 1], cols[x + 1][y + 1], cols[x][y + 1]])

        return triangles, colors

    def upload_vertices(self):
        self.vaid = GL.glGenVertexArrays(1)  # create OpenGL vertex array id
        GL.glBindVertexArray(self.vaid)  # activate to receive state below
        self.buffers = GL.glGenBuffers(2)  # create buffer for position attrib

        # create position attribute, send to GPU, declare type & per-vertex size
        GL.glEnableVertexAttribArray(0)  # assign to layout = 0 attribute
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.buffers[0])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.position, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False, 0, None)

        # create color attribute, send to GPU, declare type & per-vertex size
        GL.glEnableVertexAttribArray(1)  # assign to layout = 1 attribute
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.buffers[1])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.color, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, False, 0, None)

    def key_handler(self, key):
        if key == glfw.KEY_R:
            self.base_color[0] += 0.1
        if key == glfw.KEY_T:
            self.base_color[0] -= 0.1
        if key == glfw.KEY_LEFT:
            self.rot_angle_x += 1
        if key == glfw.KEY_RIGHT:
            self.rot_angle_x -= 1
        if key == glfw.KEY_UP:
            self.rot_angle_y += 1
        if key == glfw.KEY_DOWN:
            self.rot_angle_y -= 1
        if key == glfw.KEY_1:
            self.rot_angle_z += 1
        if key == glfw.KEY_2:
            self.rot_angle_z -= 1

    def draw(self, projection, view, model):
        global f
        s = "plotting z on the argand_plane(x,y) and  C(z).real on the z_axis"
        render_text(s, 20, 50, 1, (255, 255, 0))
        p = "vertex color values derived from C(z).imaginary"
        render_text(p, 20, 30, 1, (255, 255, 0))
        render_text("Eye U", WIDTH - 100, 10, 0.75, (0, 255, 0))

        render_text(self.f, 20, HEIGHT - 50, 1, (255, 255, 0))
        GL.glUseProgram(self.shader)
        rot_mat_x = rotate(vec(1, 0, 0), self.rot_angle_x)
        rot_mat_y = rotate(vec(0, 1, 0), self.rot_angle_y)
        rot_mat_z = rotate(vec(0, 0, 1), self.rot_angle_z)
        tra_mat = translate(0, 0, 0)
        sca_mat = scale(0.5, 0.5, 0.25)
        proj_mat = ortho(-self.n, self.n, -self.n, self.n, self.near, self.far)

        loc = GL.glGetUniformLocation(self.shader, 'global_color')
        GL.glUniform3fv(loc, 1, self.base_color)

        loc = GL.glGetUniformLocation(self.shader, 'view')
        GL.glUniformMatrix4fv(loc, 1, True, tra_mat @ rot_mat_x @ rot_mat_y @ rot_mat_z @ sca_mat)

        loc = GL.glGetUniformLocation(self.shader, 'projection')
        GL.glUniformMatrix4fv(loc, 1, True, proj_mat)

        # draw triangle as GL_TRIANGLE vertex array, draw array call
        GL.glBindVertexArray(self.vaid)
        GL.glDrawArrays(GL.GL_LINES, 0, self.size)


class Axes:
    def __init__(self, shader, n):
        self.shader = shader
        self.n = n
        positions = [(self.n, 0, 0), (-self.n, 0, 0), (0, self.n, 0), (0, -self.n, 0), (0, 0, self.n), (0, 0, -self.n)]
        colors = [(1, 1, 0), (1, 1, 0), (1, 1, 0), (1, 1, 0), (1, 1, 0), (1, 1, 0)]
        t = tuple(positions)
        position = np.array(t, 'f')
        vals = [x[2] for x in position]
        self.far = max(vals)
        self.near = min(vals)
        color = np.array(tuple(colors), 'f')
        self.size = len(position)
        self.vaid = GL.glGenVertexArrays(1)  # create OpenGL vertex array id
        GL.glBindVertexArray(self.vaid)  # activate to receive state below
        self.buffers = GL.glGenBuffers(2)  # create buffer for position attrib

        # create position attribute, send to GPU, declare type & per-vertex size
        GL.glEnableVertexAttribArray(0)  # assign to layout = 0 attribute
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.buffers[0])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, position, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False, 0, None)

        # create color attribute, send to GPU, declare type & per-vertex size
        GL.glEnableVertexAttribArray(1)  # assign to layout = 1 attribute
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.buffers[1])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, color, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, False, 0, None)

        # state variables
        self.color = [0, 0, 0]
        self.rot_angle_x = 100
        self.rot_angle_y = 0
        self.rot_angle_z = 0

    def key_handler(self, key):
        if key == glfw.KEY_R:
            self.color[0] += 0.1
        if key == glfw.KEY_T:
            self.color[0] -= 0.1
        if key == glfw.KEY_LEFT:
            self.rot_angle_x += 1
            self.rot_angle_x = self.rot_angle_x % 360
        if key == glfw.KEY_RIGHT:
            self.rot_angle_x -= 1
            self.rot_angle_x = self.rot_angle_x % 360
        if key == glfw.KEY_UP:
            self.rot_angle_y += 1
            self.rot_angle_y = self.rot_angle_y % 360
        if key == glfw.KEY_DOWN:
            self.rot_angle_y -= 1
            self.rot_angle_y = self.rot_angle_y % 360
        if key == glfw.KEY_1:
            self.rot_angle_z += 1
            self.rot_angle_z = self.rot_angle_z % 360
        if key == glfw.KEY_2:
            self.rot_angle_z -= 1
            self.rot_angle_z = self.rot_angle_z % 360

    def draw(self, projection, view, model):
        render_text('rotation_x :' + str(self.rot_angle_x), 20, 200, 1, (0, 255, 0))
        render_text('rotation_y :' + str(self.rot_angle_y), 20, 220, 1, (0, 255, 0))
        render_text('rotation_z :' + str(self.rot_angle_z), 20, 240, 1, (0, 255, 0))

        rot_mat_x = rotate(vec(1, 0, 0), self.rot_angle_x)
        rot_mat_y = rotate(vec(0, 1, 0), self.rot_angle_y)
        rot_mat_z = rotate(vec(0, 0, 1), self.rot_angle_z)
        tra_mat = translate(0, 0, 0)
        sca_mat = scale(1, 1, 1)

        GL.glUseProgram(self.shader)
        proj_mat = ortho(-self.n, self.n, -self.n, self.n, self.near, self.far)

        loc = GL.glGetUniformLocation(self.shader, 'global_color')
        GL.glUniform3fv(loc, 1, self.color)

        loc = GL.glGetUniformLocation(self.shader, 'view')
        GL.glUniformMatrix4fv(loc, 1, True, tra_mat @ rot_mat_x @ rot_mat_y @ rot_mat_z @ sca_mat)

        loc = GL.glGetUniformLocation(self.shader, 'projection')
        GL.glUniformMatrix4fv(loc, 1, True, proj_mat)

        # draw triangle as GL_TRIANGLE vertex array, draw array call
        GL.glBindVertexArray(self.vaid)
        GL.glDrawArrays(GL.GL_LINES, 0, self.size)


class Renderer:

    def __init__(self, width=WIDTH, height=HEIGHT):

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.RESIZABLE, False)
        self.win = glfw.create_window(width, height, 'Viewer', None, None)
        # glfw.hide_window(self.win)

        glfw.make_context_current(self.win)

        # event callback handlers registered
        glfw.set_key_callback(self.win, self.on_key)

        # print OpenGL renderer characteristics
        print('OpenGL', GL.glGetString(GL.GL_VERSION).decode() + ', GLSL',
              GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION).decode() +
              ', Renderer', GL.glGetString(GL.GL_RENDERER).decode())

        # clear screen
        GL.glClearColor(0.1, 0.1, 0.1, 0.1)

        # initially empty list of object to draw
        self.functions = []
        self.drawables = []

        init()
        register_window_size(width, height)

    def run(self):
        global out, close_auto
        glfw.show_window(self.win)
        while not glfw.window_should_close(self.win):
            # clear draw buffer
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            # draw the function and the axes
            self.func.draw(None, None, None)
            self.axes.draw(None, None, None)
            # flush render commands, and swap draw buffers
            glfw.swap_buffers(self.win)

            # write to mp4 file
            screenshot = glReadPixels(0, 0, WIDTH, HEIGHT, GL_BGR, GL_UNSIGNED_BYTE)
            # Convert from binary to cv2 numpy array:
            snapshot = Image.frombuffer("RGB", (WIDTH, HEIGHT), screenshot, "raw", "RGB", 0, 0)
            snapshot = np.array(snapshot)
            snapshot = cv2.flip(snapshot, 0)
            # write frame to video file:
            out.write(snapshot)

            # glfw checks for callbacks
            glfw.poll_events()

        out.release()
        close_auto = True

    def add_function(self, function):
        self.functions.append(function)

    def set_func(self, arg):
        self.func = self.functions[arg]

    def add_axes(self, axes):
        self.axes = axes

    def on_key(self, _win, key, _scancode, action, _mods):
        # 'Q' or 'Escape' quits
        global close_auto
        if action == glfw.PRESS or action == glfw.REPEAT:
            if key == glfw.KEY_ESCAPE or key == glfw.KEY_Q:
                glfw.set_window_should_close(self.win, True)
                close_auto = True

            self.axes.key_handler(key)
            self.func.key_handler(key)


# this function is run in a separate thread
# it rotates the plot as below by simulating key presses
def auto_mode(v):
    global out, close_auto
    for func_index in range(0, 8):
        v.set_func(func_index)
        v.axes.rot_angle_x = 100
        v.axes.rot_angle_y = 0
        v.axes.rot_angle_z = 0

        time.sleep(1)
        i = 0
        while not close_auto and i < 30:
            time.sleep(.75 / 12)
            v.axes.key_handler(glfw.KEY_UP)
            v.func.key_handler(glfw.KEY_UP)
            i += 1

        i = 0
        while not close_auto and i < 360:
            time.sleep(.75 / 12)
            v.axes.key_handler(glfw.KEY_1)
            v.func.key_handler(glfw.KEY_1)
            i += 1
    out.release()
    print("Auto Key key press thread exited.")


def main():
    global out
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # Open video output file:
    fn = "videoout.mp4"
    out = cv2.VideoWriter(fn, fourcc, 20.0, (WIDTH, HEIGHT))
    renderer = Renderer()
    color_shader = create_shader("color.vert", "color.frag")
    func_list = []
    func_list.append(Function(color_shader, 60, 0, 10))
    func_list.append(Function(color_shader, 60, 1, 4))
    func_list.append(Function(color_shader, 20, 2, 4))
    func_list.append(Function(color_shader, 20, 3, 4))
    func_list.append(Function(color_shader, 20, 4, 4))
    func_list.append(Function(color_shader, 20, 5, 4))
    func_list.append(Function(color_shader, 20, 6, 4))
    func_list.append(Function(color_shader, 20, 7, 4))

    for func in func_list:
        func.upload_vertices()
        renderer.add_function(func)

    renderer.add_axes(Axes(color_shader, 5))
    x = threading.Thread(target=auto_mode, args=(renderer,))
    x.start()
    # start rendering loop
    renderer.run()
    print("Main Thread exited")


if __name__ == '__main__':
    glfw.init()  # initialize window system glfw
    main()  # main function keeps variables locally scoped
    glfw.terminate()  # destroy all glfw windows and GL contexts
