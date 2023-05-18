import os


def create_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)


class MarkdownReport:
    def __init__(self, map_name, disp_count, vert_count):
        self.map_name = map_name
        self.content = '<style>img{width:55%;height:auto}</style>\n\n'

        create_dir('reports')
        create_dir('reports/images')
        create_dir(f'reports/images/{map_name}')

        self.write(f'# {map_name}\n')
        self.write(f'Total displacement count: {disp_count} \\')
        self.write(f'Total vertices count: {vert_count}')

    def next_displacement(self, idx, setpos):
        self.write(f'### Displacement {idx}')
        self.write('```')
        self.write(setpos)
        self.write('```')
        self.write('|Image|Angle|Plane dist diff|Height|Start|End|')
        self.write('|---|---|---|---|---|---|')

    def add_spot(self, img, angle, plane_dist_diff, height, start_coord, end_coord, start_power, end_power):
        img = img.split('reports/')[1]
        self.write(f'|![]({img})|{int(angle)}|{plane_dist_diff:.2f}|{height:.2f}|{start_coord}  [{start_power}]|{end_coord}  [{end_power}]|')

    def write(self, text):
        self.content += f'{text}\n'

    def save(self):
        with open(f'reports/{self.map_name}.md', 'w') as f:
            f.write(self.content)
