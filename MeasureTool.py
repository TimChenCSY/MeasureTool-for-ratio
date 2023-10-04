# MIT License

# Copyright (c) [2023] [Tim Chen]

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import tkinter as tk
import tkinter.colorchooser
from math import sqrt, atan2, degrees, acos
from itertools import combinations
import tkinter.ttk as ttk

class MeasurementTool:
    
    def __init__(self, root):
        self.root = root

        
        

        self.overlay = tk.Toplevel(self.root)
        self.overlay.geometry("1920x1080")
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-alpha', 0.4)
        self.overlay.configure(bg='grey')

        self.root.withdraw()

        self.canvas = tk.Canvas(self.overlay, bg='grey', bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Initialization of attributes
        self.initialize_attributes()

        self.show_shortcuts()

        # Bindings
        self.overlay.bind("d", self.prepare_drawing)
        self.overlay.bind("<KeyRelease-d>", self.stop_drawing)
        self.overlay.bind("f", self.start_free_drawing)
        self.overlay.bind("<KeyRelease-f>", self.stop_drawing)
        self.overlay.bind("<Escape>", self.exit_program)
        self.overlay.bind("<Control-w>", self.exit_program)
        self.undo_stack = []
        self.overlay.bind("<Control-z>", self.undo_last_action)  # Bind undo to Ctrl+Z
        self.overlay.bind("<Control-r>", self.clear_screen)  # Bind clear screen to Ctrl+R
        # self.overlay.bind("s", self.toggle_snapping_on)
        # self.overlay.bind("<KeyRelease-s>", self.toggle_snapping_off)
        self.overlay.bind("s", self.toggle_snapping)
        self.shift_held = False
        self.overlay.bind("<Shift_L>", self.shift_pressed)
        self.overlay.bind("<KeyRelease-Shift_L>", self.shift_released)      
        self.settings_window = None
        self.overlay.bind("i", self.open_settings)



    def initialize_attributes(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.current_line = None
        self.reference_line = None
        self.lines = []
        self.selected_vertex = None
        self.vertex_highlight = None
        self.selected_vertex_highlight = None
        self.drawing_mode = None
        self.line_drawn = False
        self.reference_line_length = None
        self.ratio_display = None
        self.angle_display = None
        self.snapping_mode = False
        self.temp_intersection_angles = []

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        self.mouse_x_line = self.canvas.create_line(0, 0, 0, self.canvas.winfo_height(), fill='darkgrey', dash=(4, 2))
        self.mouse_y_line = self.canvas.create_line(0, 0, self.canvas.winfo_width(), 0, fill='darkgrey', dash=(4, 2))

        
    def open_settings(self, event=None):
        if self.settings_window:
            self.settings_window.destroy()
        self.settings_window = SettingsWindow(self)
        
    def prepare_drawing(self, event=None):
        if not self.selected_vertex:
            self.start_free_drawing()
        else:
            self.drawing_mode = "d"
            self.start_x, self.start_y = self.selected_vertex

    def start_free_drawing(self, event=None):
        self.drawing_mode = "f"

    def stop_drawing(self, event):
        self.drawing_mode = None
        self.start_x, self.start_y = None, None
        self.line_drawn = False

    def toggle_snapping_on(self, event=None):
        """Enable the snapping mode."""
        self.snapping_mode = True

    def toggle_snapping_off(self, event=None):
        """Disable the snapping mode."""
        self.snapping_mode = False

    def show_shortcuts(self):
        shortcuts = """
        Shortcuts | 快捷方式:
        ------------------
        d: Draw from vertex | 从顶点绘制
        f: Free draw | 自由绘制
        Shift: Snap to axis | 吸附到轴
        s: Toggle snapping | 切换吸附模式
        Ctrl + z: Undo | 撤销
        Ctrl + r: Clear all | 清除所有
        Escape/Ctrl + w: Exit | 退出
        i: Settings | 设置
        """
        self.shortcuts_label = tk.Label(self.canvas, text=shortcuts, bg='white', justify='left', anchor='nw')
        self.shortcuts_label.place(relx=0, rely=0, anchor='nw')

    def on_click(self, event):
        if self.drawing_mode == "d" and self.selected_vertex:
            self.start_x, self.start_y = self.selected_vertex
        elif self.drawing_mode == "f":
            self.start_x, self.start_y = event.x, event.y

        # Check if the click is for selecting/deselecting a vertex or line
        for line, data in self.lines:
            x1, y1, x2, y2 = self.canvas.coords(line)
            
            # Check for vertices first
            if abs(x1 - event.x) < 10 and abs(y1 - event.y) < 10:
                self.selected_vertex = (x1, y1)
                self.update_selected_vertex_highlight()
                self.toggle_reference_line(line)
                return
            elif abs(x2 - event.x) < 10 and abs(y2 - event.y) < 10:
                self.selected_vertex = (x2, y2)
                self.update_selected_vertex_highlight()
                self.toggle_reference_line(line)
                return

            # Check for line selection
            coords = self.canvas.coords(line)
            dist = self.point_to_line_distance(coords, (event.x, event.y))
            if dist < 5:
                self.toggle_reference_line(line)
                return

    def on_drag(self, event):
        # If not in drawing mode or start coordinates are not defined, simply return
        if not self.drawing_mode or self.start_x is None or self.start_y is None:
            return
        
        # If there's a current line being drawn, remove it
        if self.current_line:
            self.canvas.delete(self.current_line)

        # If SHIFT is held or in snapping mode, adjust the end point
        if self.shift_held:
            dx = abs(event.x - self.start_x)
            dy = abs(event.y - self.start_y)
            if dx > dy:
                event.y = self.start_y  # make it horizontal
            else:
                event.x = self.start_x  # make it vertical
        elif self.snapping_mode:
            nearest_vertex = self.get_nearest_vertex(event.x, event.y)
            if nearest_vertex:
                event.x, event.y = nearest_vertex

        # Create a new line
        self.current_line = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, width=2)
        self.line_drawn = True
        


        # Calculate and display ratio if reference line exists
        if self.reference_line_length and self.start_x is not None and self.start_y is not None:
            current_length = sqrt((event.x - self.start_x)**2 + (event.y - self.start_y)**2)
            ratio = current_length / self.reference_line_length
            midpoint_x = (self.start_x + event.x) / 2
            midpoint_y = (self.start_y + event.y) / 2
            if self.ratio_display:
                self.canvas.delete(self.ratio_display)
            self.ratio_display = self.canvas.create_text(midpoint_x, midpoint_y, text=f"{ratio:.2f}", anchor="center")




        # Calculate and display the angle in relation to the horizontal axis
        angle = self.calculate_line_angle(self.start_x, self.start_y, event.x, event.y)
        angle_text = f"{angle:.1f}°"
        if self.angle_display:
            self.canvas.delete(self.angle_display)
        self.angle_display = self.canvas.create_text((self.start_x + event.x) / 2, (self.start_y + event.y) / 2 - 30, text=angle_text, anchor="center", fill="red")

        # If there's a currently drawn line, check for intersections and display angles
        if self.line_drawn:
            self.update_temp_intersection_angles(event.x, event.y)
        
        self.highlight_nearby_vertex(event.x, event.y)

        self.update_mouse_axis_lines(event.x, event.y)

    def toggle_snapping(self, event=None):
        """Toggle the snapping mode."""
        self.snapping_mode = not self.snapping_mode

    def on_release(self, event):
        if not self.line_drawn:
            return
        
        if self.shift_held:
            dx = abs(event.x - self.start_x)
            dy = abs(event.y - self.start_y)
            if dx > dy:
                event.y = self.start_y  # make it horizontal
            else:
                event.x = self.start_x  # make it vertical

        elif self.snapping_mode:
            nearest_vertex = self.get_nearest_vertex(event.x, event.y)
            if nearest_vertex:
                self.end_x, self.end_y = nearest_vertex
                event.x, event.y = nearest_vertex
        else:
            self.end_x = event.x
            self.end_y = event.y

        if self.shift_held:
            dx = abs(event.x - self.start_x)
            dy = abs(event.y - self.start_y)
            if dx > dy:
                event.y = self.start_y  # make it horizontal
            else:
                event.x = self.start_x  # make it vertical
        
        length = sqrt((event.x - self.start_x)**2 + (event.y - self.start_y)**2)

        # If it's a simple click without dragging, return early
        if length < 2:
            return

         # Store the line data and make the end point of the line the currently selected vertex
        line_data = {'coords': (self.start_x, self.start_y, event.x, event.y), 'length': length, 'ratio_display': None, 'angle_display': None}
        self.lines.append((self.current_line, line_data))
        self.selected_vertex = (event.x, event.y)
        self.current_line = None

        self.selected_vertex = (self.end_x, self.end_y)
        self.update_selected_vertex_highlight()

        if len(self.lines) == 1:
            self.set_reference_line(self.lines[0][0])

        # Remove the temporary ratio display
        if self.ratio_display:
            self.canvas.delete(self.ratio_display)
            self.ratio_display = None

        # Remove the temporary angle display
        if self.angle_display:
            self.canvas.delete(self.angle_display)
            self.angle_display = None

        # Delete temporary intersection angles
        if self.temp_intersection_angles:
            for angle_display in self.temp_intersection_angles:
                self.canvas.delete(angle_display)
            self.temp_intersection_angles = []

       

        # Calculate and display the angle in relation to the horizontal axis
        angle = self.calculate_line_angle(self.start_x, self.start_y, event.x, event.y)
        angle_text = f"{angle:.1f}°"
        angle_display = self.canvas.create_text((self.start_x + event.x) / 2, (self.start_y + event.y) / 2 - 30, text=angle_text, anchor="center", fill="red")
        line_data['angle_display'] = angle_display

        # Update ratios for all lines
        self.update_all_ratios()
        # Update intersection angles for all lines
        self.update_intersection_angles()
        # Update intersection angles for all lines
        self.update_all_intersection_angles()

        self.highlight_nearby_vertex(event.x, event.y)

    def on_mouse_move(self, event):
        # Remove previous vertex highlights
        if self.vertex_highlight:
            self.canvas.delete(self.vertex_highlight)
            self.vertex_highlight = None

        nearest_vertex = None
        min_distance = float('inf')

        # Check for nearby vertices and highlight them
        for line, data in self.lines:
            x1, y1, x2, y2 = self.canvas.coords(line)
            d1 = sqrt((x1 - event.x)**2 + (y1 - event.y)**2)
            d2 = sqrt((x2 - event.x)**2 + (y2 - event.y)**2)

            if d1 < 10 and d1 < min_distance:
                nearest_vertex = (x1, y1)
                min_distance = d1
            if d2 < 10 and d2 < min_distance:
                nearest_vertex = (x2, y2)
                min_distance = d2

        # Only create the yellow highlight if it's not the currently selected vertex
        if nearest_vertex and nearest_vertex != self.selected_vertex:
            x, y = nearest_vertex
            self.vertex_highlight = self.canvas.create_oval(x-5, y-5, x+5, y+5, fill='yellow')

        self.update_mouse_axis_lines(event.x, event.y)

    def update_mouse_axis_lines(self, x, y):
        """Update the position of the mouse axis lines."""
        self.canvas.coords(self.mouse_x_line, x, 0, x, self.canvas.winfo_height())
        self.canvas.coords(self.mouse_y_line, 0, y, self.canvas.winfo_width(), y)


    def highlight_nearby_vertex(self, x, y):
        # Remove previous vertex highlights
        if self.vertex_highlight:
            self.canvas.delete(self.vertex_highlight)
            self.vertex_highlight = None

        nearest_vertex = None
        min_distance = float('inf')

        # Check for nearby vertices and highlight them
        for line, data in self.lines:
            x1, y1, x2, y2 = self.canvas.coords(line)
            d1 = sqrt((x1 - x)**2 + (y1 - y)**2)
            d2 = sqrt((x2 - x)**2 + (y2 - y)**2)

            if d1 < 10 and d1 < min_distance:
                nearest_vertex = (x1, y1)
                min_distance = d1
            if d2 < 10 and d2 < min_distance:
                nearest_vertex = (x2, y2)
                min_distance = d2

        

        # Only create the yellow highlight if it's not the currently selected vertex
        if nearest_vertex and nearest_vertex != self.selected_vertex:
            x, y = nearest_vertex
            self.vertex_highlight = self.canvas.create_oval(x-5, y-5, x+5, y+5, fill='yellow')

    def exit_program(self, event):
        self.root.destroy()

    def update_selected_vertex_highlight(self):
        # Remove previous selected vertex highlight
        if self.selected_vertex_highlight:
            self.canvas.delete(self.selected_vertex_highlight)
            self.selected_vertex_highlight = None
            
        # Highlight the selected vertex in green
        if self.selected_vertex:
            x, y = self.selected_vertex
            self.selected_vertex_highlight = self.canvas.create_oval(x-5, y-5, x+5, y+5, fill='green')

    def point_to_line_distance(self, line_coords, point):
        """Calculate shortest distance between a point and a line segment."""
        x1, y1, x2, y2 = line_coords
        px, py = point
        line_len = sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_len == 0:
            return sqrt((x1 - px)**2 + (y1 - py)**2)
        t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_len**2
        t = max(0, min(1, t))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        return sqrt((proj_x - px)**2 + (proj_y - py)**2)

    def set_reference_line(self, line):
        if self.reference_line:
            self.remove_reference_line()
        self.reference_line = line
        self.canvas.itemconfig(self.reference_line, fill='blue')
        _, data = next((l, d) for l, d in self.lines if l == self.reference_line)
        self.reference_line_length = data['length']

        # Update ratios for all lines
        self.update_all_ratios()



    def remove_reference_line(self):
        if self.reference_line:
            self.canvas.itemconfig(self.reference_line, fill='black')
            self.reference_line = None
            self.reference_line_length = None

            # Update ratios for all lines
            self.update_all_ratios()

    def toggle_reference_line(self, line):
        if self.reference_line == line:
            self.remove_reference_line()
        else:
            self.set_reference_line(line)

    def update_all_ratios(self):
        for line, data in self.lines:
            x1, y1, x2, y2 = data['coords']
            if 'ratio_display' in data and data['ratio_display']:
                self.canvas.delete(data['ratio_display'])

            if self.reference_line_length:
                ratio = data['length'] / self.reference_line_length
                midpoint_x = (x1 + x2) / 2
                midpoint_y = (y1 + y2) / 2
                # Display ratio above the line to avoid overlap
                data['ratio_display'] = self.canvas.create_text(midpoint_x, midpoint_y - 10, text=f"{ratio:.2f}", anchor="center")
            else:
                data['ratio_display'] = None
             # Update the position of the ratio text

            midpoint_x = (x1 + x2) / 2
            midpoint_y = (y1 + y2) / 2
            if data['ratio_display']:
                self.update_ratio_position(x1, y1, x2, y2, midpoint_x, midpoint_y, data['ratio_display'])
        
    def update_ratio_position(self, x1, y1, x2, y2, midpoint_x, midpoint_y, text_obj):
        """Determine the optimal position for the ratio text based on the line's orientation."""

        angle = degrees(atan2(y2 - y1, x2 - x1))
        if -45 <= angle <= 45:
            # Horizontal-ish line
            self.canvas.coords(text_obj, midpoint_x, midpoint_y - 20)
        elif 45 < angle < 135:
            # Vertical-ish line (positive slope)
            self.canvas.coords(text_obj, midpoint_x - 20, midpoint_y)
        elif -135 < angle < -45:
            # Vertical-ish line (negative slope)
            self.canvas.coords(text_obj, midpoint_x + 20, midpoint_y)
        else:
            # Horizontal-ish line (but inverted)
            self.canvas.coords(text_obj, midpoint_x, midpoint_y + 20)

    def undo_last_action(self, event=None):
        """Undo the last drawn or modified line."""
        if self.lines:
            line_to_remove, line_data = self.lines.pop()
            
            # Delete the line
            self.canvas.delete(line_to_remove)
            
            # Delete the associated ratio display, if it exists
            if line_data['ratio_display']:
                self.canvas.delete(line_data['ratio_display'])

            # Delete the associated angle display, if it exists
            if line_data['angle_display']:
                self.canvas.delete(line_data['angle_display'])

            # Delete intersection angles, if they exist
            if 'intersection_angles' in line_data:
                for angle_display in line_data['intersection_angles']:
                    self.canvas.delete(angle_display)


            # If the reference line is deleted, remove it as reference
            if self.reference_line == line_to_remove:
                self.remove_reference_line()

            # Update ratios for all remaining lines
            self.update_all_ratios()

            self.update_all_intersection_angles()


    def clear_screen(self, event=None):
        """Clear all lines and reset the tool's state."""
        for line, line_data in self.lines:
            # Delete the line
            self.canvas.delete(line)
            
            # Delete the associated ratio display, if it exists
            if line_data['ratio_display']:
                self.canvas.delete(line_data['ratio_display'])
          
            if line_data['angle_display']:
                self.canvas.delete(line_data['angle_display'])

            for _, data in self.lines:
                if 'intersection_angles' in data:
                    for angle_display in data['intersection_angles']:
                        self.canvas.delete(angle_display)



        # Delete vertex highlights
        if self.vertex_highlight:
            self.canvas.delete(self.vertex_highlight)
            self.vertex_highlight = None
            
        # Delete selected vertex highlights
        if self.selected_vertex_highlight:
            self.canvas.delete(self.selected_vertex_highlight)
            self.selected_vertex_highlight = None

        # Clear the list of lines
        self.lines.clear()

        # Remove any set reference line
        self.remove_reference_line()
        
        # Reinitialize the tool's attributes
        self.initialize_attributes()

    def calculate_line_angle(self, x1, y1, x2, y2):
        """Determine the angle of the line in relation to the horizontal axis (0° to 90°)."""
        dx = x2 - x1
        dy = y2 - y1
        angle = abs(degrees(atan2(dy, dx)))
        return angle if angle <= 90 else 180 - angle

    def update_intersection_angles(self):
        # Clear previous intersection angles
        for _, data in self.lines:
            if 'intersection_angles' in data:
                for angle_display in data['intersection_angles']:
                    self.canvas.delete(angle_display)
                data['intersection_angles'] = []

        # Check every pair of lines for intersections
        for (line1, data1), (line2, data2) in combinations(self.lines, 2):
            x1, y1, x2, y2 = data1['coords']
            x3, y3, x4, y4 = data2['coords']

            # Check for common vertex and calculate angle
            common_vertex = None
            if (x1, y1) == (x3, y3):
                common_vertex = (x1, y1)
            elif (x1, y1) == (x4, y4):
                common_vertex = (x1, y1)
            elif (x2, y2) == (x3, y3):
                common_vertex = (x2, y2)
            elif (x2, y2) == (x4, y4):
                common_vertex = (x2, y2)
            
            if common_vertex:
                angle = self.angle_between_two_lines((x1, y1, x2, y2), (x3, y3, x4, y4))
                angle_text = f"{angle:.1f}°"
                angle_display = self.canvas.create_text(common_vertex[0], common_vertex[1] - 20, text=angle_text, anchor="center", fill="purple")
                if 'intersection_angles' not in data1:
                    data1['intersection_angles'] = []
                data1['intersection_angles'].append(angle_display)

  

    def angle_between_two_lines(self, line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        # Identify the common vertex and compute the vectors u and v
        if (x1, y1) == (x3, y3):
            u = (x2 - x1, y2 - y1)
            v = (x4 - x3, y4 - y3)
        elif (x1, y1) == (x4, y4):
            u = (x2 - x1, y2 - y1)
            v = (x3 - x4, y3 - y4)
        elif (x2, y2) == (x3, y3):
            u = (x1 - x2, y1 - y2)
            v = (x4 - x3, y4 - y3)
        else:
            u = (x1 - x2, y1 - y2)
            v = (x3 - x4, y3 - y4)

        # Normalize the vectors
        magnitude_u = sqrt(u[0]**2 + u[1]**2)
        magnitude_v = sqrt(v[0]**2 + v[1]**2)
        u = (u[0]/magnitude_u, u[1]/magnitude_u)
        v = (v[0]/magnitude_v, v[1]/magnitude_v)

        # Compute the dot product
        dot_product = u[0] * v[0] + u[1] * v[1]
        
        # Ensure the value lies between -1 and 1 to avoid ValueError due to floating point inaccuracies
        cos_theta = max(-1, min(1, dot_product))
        
        angle = degrees(acos(cos_theta))

        return angle


    
    def update_temp_intersection_angles(self, x, y):
        # Clear previous temporary intersection angles
        if self.temp_intersection_angles:
            for angle_display in self.temp_intersection_angles: 
                self.canvas.delete(angle_display)
            self.temp_intersection_angles = []

        for line, data in self.lines:
            x1, y1, x2, y2 = data['coords']
            common_vertex = None
            if (x1, y1) == (self.start_x, self.start_y):
                common_vertex = (x1, y1)
            elif (x2, y2) == (self.start_x, self.start_y):
                common_vertex = (x2, y2)

            if common_vertex:
                angle = self.angle_between_two_lines((x1, y1, x2, y2), (self.start_x, self.start_y, x, y))
                # if angle > 90:
                #     angle = 180 - angle
                angle_text = f"{angle:.1f}°"
                offset_x = (common_vertex[0] + x) / 2
                offset_y = (common_vertex[1] + y) / 2 - 20
                angle_display = self.canvas.create_text(offset_x, offset_y, text=angle_text, anchor="center", fill="purple")
                if not self.temp_intersection_angles:
                    self.temp_intersection_angles = []
                self.temp_intersection_angles.append(angle_display)

    def update_all_intersection_angles(self):
        # Clear previous intersection angles
        for _, data in self.lines:
            if 'intersection_angles' in data:
                for angle_display in data['intersection_angles']:
                    self.canvas.delete(angle_display)
                data['intersection_angles'] = []

        for (line1, data1), (line2, data2) in combinations(self.lines, 2):
            x1, y1, x2, y2 = data1['coords']
            x3, y3, x4, y4 = data2['coords']

            common_vertex = None
            if (x1, y1) == (x3, y3):
                common_vertex = (x1, y1)
            elif (x1, y1) == (x4, y4):
                common_vertex = (x1, y1)
            elif (x2, y2) == (x3, y3):
                common_vertex = (x2, y2)
            elif (x2, y2) == (x4, y4):
                common_vertex = (x2, y2)

            if common_vertex:
                angle = self.angle_between_two_lines((x1, y1, x2, y2), (x3, y3, x4, y4))
                # if angle > 90:
                #     angle = 180 - angle
                angle_text = f"{angle:.1f}°"
                offset_x = (common_vertex[0] + (x1 + x2 + x3 + x4) / 4) / 2
                offset_y = (common_vertex[1] + (y1 + y2 + y3 + y4) / 4) / 2 - 20
                angle_display = self.canvas.create_text(offset_x, offset_y, text=angle_text, anchor="center", fill="purple")
                if 'intersection_angles' not in data1:
                    data1['intersection_angles'] = []
                data1['intersection_angles'].append(angle_display)

    def get_nearest_vertex(self, x, y):
        """Return the nearest vertex if within snapping distance, otherwise return None."""
        SNAP_DISTANCE = 15  # Define a threshold for snapping
        nearest_vertex = None
        min_distance = float('inf')
        
        for line, data in self.lines:
            x1, y1, x2, y2 = self.canvas.coords(line)
            
            d1 = sqrt((x1 - x)**2 + (y1 - y)**2)
            d2 = sqrt((x2 - x)**2 + (y2 - y)**2)
            
            if d1 < SNAP_DISTANCE and d1 < min_distance:
                nearest_vertex = (x1, y1)
                min_distance = d1
            if d2 < SNAP_DISTANCE and d2 < min_distance:
                nearest_vertex = (x2, y2)
                min_distance = d2
                
        return nearest_vertex
    
    def shift_pressed(self, event):
        self.shift_held = True

    def shift_released(self, event):
        self.shift_held = False

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent.overlay)
        self.title("Settings | 设置")
        self.parent = parent
        self.notebook = ttk.Notebook(self)

        # Main settings tab
        self.settings_frame = tk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings | 设置")
        
        # User manual tab
        self.manual_frame = tk.Frame(self.notebook)
        self.notebook.add(self.manual_frame, text="User Manual | 用户手册")
        self.populate_manual_frame()

        # User manual tab
        self.license_frame = tk.Frame(self.notebook)
        self.notebook.add(self.license_frame, text="MIT License")
        self.a_license_frame()

        self.notebook.pack(expand=True, fill='both')

        # Bind to the parent's click event to detect clicks outside the window
        self.parent.overlay.bind('<Button-1>', self.check_close)

        # Colors
        self.colors = ["white", "grey", "black"]
        self.color_var = tk.StringVar(value=self.colors[1])
        self.color_label = tk.Label(self.settings_frame, text="Background Color | 背景颜色:")
        self.color_label.pack(anchor='w', padx=10, pady=5)
        for color in self.colors:
            rb = tk.Radiobutton(self.settings_frame, text=color, variable=self.color_var, value=color, command=self.apply_background_color)
            rb.pack(anchor="w", padx=10, pady=2)

        # Transparency
        self.transparency_label = tk.Label(self.settings_frame, text="Background Transparency | 背景透明度:")
        self.transparency_label.pack(anchor='w', padx=10, pady=5)
        self.transparency_slider = tk.Scale(self.settings_frame, from_=0, to_=1, orient="horizontal", resolution=0.05, command=self.apply_transparency)
        self.transparency_slider.set(0.4)  # default value
        self.transparency_slider.pack(anchor='w', padx=10, pady=5, fill="x")

        # Line Thickness
        self.line_thickness_label = tk.Label(self.settings_frame, text="Line Thickness | 线条粗细:")
        self.line_thickness_label.pack(anchor='w', padx=10, pady=5)
        self.line_thickness_slider = tk.Scale(self.settings_frame, from_=1, to_=10, orient="horizontal", resolution=0.5, command=self.apply_line_thickness)
        self.line_thickness_slider.set(2)  # default value
        self.line_thickness_slider.pack(anchor='w', padx=10, pady=5, fill="x")

        # Font Size and Color for angles
        self.font_size_label = tk.Label(self.settings_frame, text="Font Size for Angles | 角度的字体大小:")
        self.font_size_label.pack(anchor='w', padx=10, pady=5)
        self.font_size_slider = tk.Scale(self.settings_frame, from_=0, to_=40, orient="horizontal", command=self.apply_font_size)
        self.font_size_slider.set(12)  # default value
        self.font_size_slider.pack(anchor='w', padx=10, pady=5, fill="x")

        # Font Size for Ratio
        self.ratio_font_size_label = tk.Label(self.settings_frame, text="Font Size for Ratio | 比率的字体大小:")
        self.ratio_font_size_label.pack(anchor='w', padx=10, pady=5)
        self.ratio_font_size_slider = tk.Scale(self.settings_frame, from_=0, to_=40, orient="horizontal", command=self.apply_ratio_font_size)
        self.ratio_font_size_slider.set(12)  # default value
        self.ratio_font_size_slider.pack(anchor='w', padx=10, pady=5, fill="x")

        # Font Size for Intersection Angles
        self.intersection_font_size_label = tk.Label(self.settings_frame, text="Font Size for Intersection Angles | 交点角度的字体大小:")
        self.intersection_font_size_label.pack(anchor='w', padx=10, pady=5)
        self.intersection_font_size_slider = tk.Scale(self.settings_frame, from_=0, to_=40, orient="horizontal", command=self.apply_intersection_font_size)
        self.intersection_font_size_slider.set(12)  # default value
        self.intersection_font_size_slider.pack(anchor='w', padx=10, pady=5, fill="x")

        # Font Color for Angles
        self.font_colors = ["red", "green", "blue", "black"]
        self.font_color_var = tk.StringVar(value=self.font_colors[0])
        self.font_color_label = tk.Label(self.settings_frame, text="Font Color for Angles | 角度的字体颜色:")
        self.font_color_label.pack(anchor='w', padx=10, pady=5)
        for color in self.font_colors:
            rb = tk.Radiobutton(self.settings_frame, text=color, variable=self.font_color_var, value=color, command=self.apply_font_color)
            rb.pack(anchor="w", padx=10, pady=2)

    def a_license_frame(self):
        mit_license = """
        
        被授权人权利
        特此授予任何人免费获得本软件和相关文档文件（“软件”）副本的许可，不受限制地处理本软件，
        包括但不限于使用、复制、修改、合并 、发布、分发、再许可的权利， 被授权人有权利使用、
        复制、修改、合并、出版发行、散布、再授权和/或贩售软体及软体的副本，
        及授予被供应人同等权利，惟服从以下义务。

        被授权人义务
        在软体和软体的所有副本中都必须包含以上版权声明和本许可声明。

        MIT License

        Copyright (c) [2023] [Tim Chen]

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.



"""
        license_label = tk.Label(self.license_frame, text=mit_license, justify='left')
        license_label.pack(padx=10, pady=10, anchor='w')



    def populate_manual_frame(self):
        user_manual = """
        User Manual | 用户手册:

        This is a little tool to to help you measure ratios and angles on screen
        这是一个用来帮你量屏幕上的比例和角度的小工具

        Free and open source|完全免费开源

        ----------------------
        - Lines can be drawn and selected as tha reference line
        - Red angles ane their angles related to a coordinate system's x-axis
        - Purple angles are their angle related to connected lines
        - 线可以被绘制并选取为参考线
        - 红色角度是一条线与一个坐标系正X轴之间的夹角
        - 紫色角度是他们与共享同一个端点的相连线之间的夹角

        ----------------------
        - Draw Lines:
        Press and hold 'd' to start drawing from a selected vertex. | 按住 'd' 从所选的顶点开始绘制。
        Press and hold 'f' to start free drawing from any point. | 按住 'f' 从任意点开始自由绘制。
        Use 'Shift' key to snap the line to horizontal or vertical. | 使用 'Shift' 键将线条对齐到水平或垂直。

        - Select and Measure:
        Click on a line's end to select. | 点击线的端点进行选择。
        Lines display the angle with horizontal. | 线显示与水平线的角度。
        Intersecting lines show the angle of intersection. | 相交线显示相交角。

        - Reference Line:
        Click on a line to set as reference. The line turns blue. | 点击一条线将其设置为参考线，该线会变为蓝色。
        Draw lines to see the ratio to the reference line's length. | 绘制线条查看与参考线长度的比例。
        Click on the reference line again to deselect. | 再次点击参考线以取消选择。

        - Snapping Mode:
        Press 's' to toggle snapping mode. | 按 's' 切换对齐模式。
        
        - Undo & Clear:
        Press 'Ctrl + z' to undo last action. | 按 'Ctrl + z' 撤销上一个操作。
        Press 'Ctrl + r' to clear all drawings. | 按 'Ctrl + r' 清除所有绘图。
        
        - Exit:i
        Press 'Escape' or 'Ctrl + w' to exit program. | 按 'Escape' 或 'Ctrl + w' 退出程序。

        - Settings:
        Press 'i' to open settings. | 按 'i' 打开设置。
        
        - Creator's note|作者留言:
        This little tool is created by Tim Chen 2023 inspired by DoudouTown drawing exercise. 
        Fully developed with Chatgpt in 2 days. | 
        这个小工具由Tim受到抖抖村课程启发而制作 (或许他只是想逃避练习画画). 花了两天时间在chatGPT帮助下实现. 
        If the mouse was released during drawing, the line won't be set.| 如果鼠标在绘画时提前松开, 线不会被记录
        If multiple lines are connected to the same vertex it might get hard to read | 
        如果许多线连接到同一个端点会很难读

        If there's a bug try to restart | 如果有bug请重启
        
        """
        manual_label = tk.Label(self.manual_frame, text=user_manual, justify='left')
        manual_label.pack(padx=10, pady=10, anchor='w')



    def apply_background_color(self):
        color = self.color_var.get()
        self.parent.overlay.configure(bg=color)
        self.parent.canvas.configure(bg=color)

    def apply_transparency(self, value):
        self.parent.overlay.attributes('-alpha', float(value))

    def apply_line_thickness(self, value):
        for line, data in self.parent.lines:
            self.parent.canvas.itemconfig(line, width=float(value))

    def apply_font_size(self, value):
        font_size = int(value)
        for line, data in self.parent.lines:
            if 'angle_display' in data and data['angle_display']:
                self.parent.canvas.itemconfig(data['angle_display'], font=('Arial', font_size))

    def apply_ratio_font_size(self, value):
        font_size = int(value)
        for line, data in self.parent.lines:
            if 'ratio_display' in data and data['ratio_display']:
                self.parent.canvas.itemconfig(data['ratio_display'], font=('Arial', font_size))

    def apply_font_color(self):
        color = self.font_color_var.get()
        for line, data in self.parent.lines:
            if 'angle_display' in data and data['angle_display']:
                self.parent.canvas.itemconfig(data['angle_display'], fill=color)

    def check_close(self, event=None):
        # Check if the click event happened outside the window
        if event:
            if not (self.winfo_x() < event.x_root < self.winfo_x() + self.winfo_width() and
                    self.winfo_y() < event.y_root < self.winfo_y() + self.winfo_height()):
                self.destroy()
    def apply_intersection_font_size(self, value):
        font_size = int(value)
        for line, data in self.parent.lines:
            if 'intersection_angles' in data and data['intersection_angles']:
                self.parent.canvas.itemconfig(data['intersection_angles'], font=('Arial', font_size))


if __name__ == "__main__":
    root = tk.Tk()
    tool = MeasurementTool(root)
    root.mainloop()