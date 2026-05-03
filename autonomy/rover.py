class Rover:
    def __init__(self, pos, energia=100, H=180, W=360):
        self.pos    = pos
        self.energia = energia
        self.historico = []
        self.H = H
        self.W = W

    def mover(self, direcao, custo=1):
        if direcao == "N":
            self.pos[0] += 1
        elif direcao == "S":
            self.pos[0] -= 1
        elif direcao == "E":
            self.pos[1] += 1
        elif direcao == "W":
            self.pos[1] -= 1

        # Garante que posição fique dentro dos bounds do grid
        self.pos[0] = max(0, min(self.pos[0], self.H - 1))
        self.pos[1] = self.pos[1] % self.W   # longitude é circular

        self.energia -= custo
        self.historico.append(tuple(self.pos))

    def get_pos(self):
        return self.pos