import freetype
import glm
import numpy as np
from OpenGL.GL import *
# had to install PyGLM and freetype-py
from OpenGL.GL import shaders

fontfile = "cour.ttf"

VERTEX_SHADER = """
        #version 330 core
        layout (location = 0) in vec4 vertex; // <vec2 pos, vec2 tex>
        out vec2 TexCoords;

        uniform mat4 projection;

        void main()
        {
            gl_Position = projection * vec4(vertex.xy, 0.0, 1.0);
            TexCoords = vertex.zw;
        }
       """

FRAGMENT_SHADER = """
        #version 330 core
        in vec2 TexCoords;
        out vec4 color;

        uniform sampler2D text;
        uniform vec3 textColor;

        void main()
        {    
            vec4 sampled = vec4(1.0, 1.0, 1.0, texture(text, TexCoords).r);
            color = vec4(textColor, 1.0) * sampled;
        }
        """

shaderProgram = None
Characters = dict()
VBO = None
VAO = None


class CharacterSlot:
    def __init__(self, texture, glyph):
        self.TextureID = texture
        self.Size_x = glyph.bitmap.width
        self.Size_y = glyph.bitmap.rows
        self.Bearing_x = glyph.bitmap_left
        self.Bearing_y = glyph.bitmap_top
        self.Advance = glyph.advance.x


def register_window_size(w, h):
    shader_projection = glGetUniformLocation(shaderProgram, "projection")
    projection = glm.ortho(0, w, 0, h)
    glUniformMatrix4fv(shader_projection, 1, GL_FALSE, glm.value_ptr(projection))


def init():
    global VERTEXT_SHADER
    global FRAGMENT_SHADER
    global shaderProgram
    global Characters
    global VBO
    global VAO

    VAO = glGenVertexArrays(1)
    glBindVertexArray(VAO)

    # compile shaders
    vertexshader = shaders.compileShader(VERTEX_SHADER, GL_VERTEX_SHADER)
    fragmentshader = shaders.compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
    shaderProgram = shaders.compileProgram(vertexshader, fragmentshader)

    glUseProgram(shaderProgram)

    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    face = freetype.Face(fontfile)
    face.set_pixel_sizes(0, 24)

    # load first 128 characters of ASCII set
    for i in range(0, 128):
        face.load_char(chr(i))
        glyph = face.glyph

        # generate texture
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, glyph.bitmap.width, glyph.bitmap.rows, 0, GL_RED, GL_UNSIGNED_BYTE,
                     glyph.bitmap.buffer)

        # texture options
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        # now store character for later use
        Characters[chr(i)] = CharacterSlot(texture, glyph)

    glBindTexture(GL_TEXTURE_2D, 0)

    # configure VAO/VBO for texture quads
    VBO = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, 4 * 6 * 4, None, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)


def render_text(text, x, y, scale, color):
    global shaderProgram
    global Characters
    global VBO
    global VAO

    glUseProgram(shaderProgram)
    glUniform3f(glGetUniformLocation(shaderProgram, "textColor"), color[0] / 255, color[1] / 255, color[2] / 255)
    glActiveTexture(GL_TEXTURE0)
    glBindVertexArray(VAO)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    for c in text:
        ch = Characters[c]
        xpos = x + ch.Bearing_x * scale
        ypos = y - (ch.Size_y - ch.Bearing_y) * scale
        w = ch.Size_x * scale
        h = ch.Size_y * scale
        vertices = np.asarray([
            xpos, ypos + h, 0.0, 0.0,
            xpos, ypos, 0.0, 1.0, xpos + w, ypos, 1.0, 1.0,
            xpos, ypos + h, 0.0, 0.0, xpos + w, ypos, 1.0, 1.0, xpos + w, ypos + h, 1.0, 0.0
        ], np.float32)

        # render glyph texture over quad
        glBindTexture(GL_TEXTURE_2D, ch.TextureID)
        # update content of VBO memory
        glBindBuffer(GL_ARRAY_BUFFER, VBO)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        # render quad
        glDrawArrays(GL_TRIANGLES, 0, 6)
        # now advance cursors for next glyph (note that advance is number of 1/64 pixels)
        x += (ch.Advance >> 6) * scale

    glBindVertexArray(0)
    glBindTexture(GL_TEXTURE_2D, 0)
