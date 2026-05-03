from .strategy import escolher_movimento


class Planner:

    def __init__(self, rover, ambiente):
        self.rover = rover
        self.ambiente = ambiente

    def passo(self):
        mov = escolher_movimento(self.rover, self.ambiente)

        # custo do movimento baseado no ambiente
        nova_pos = self._simular_pos(self.rover.pos, mov)
        custo = self.ambiente.get_custo(nova_pos)

        self.rover.mover(mov, custo)

        return mov

    def _simular_pos(self, pos, direcao):
        nova_pos = pos.copy()

        if direcao == "N":
            nova_pos[0] += 1
        elif direcao == "S":
            nova_pos[0] -= 1
        elif direcao == "E":
            nova_pos[1] += 1
        elif direcao == "W":
            nova_pos[1] -= 1

        # Clip usando dimensões reais do ambiente
        if self.ambiente._arr_insol is not None:
            H, W = self.ambiente._arr_insol.shape
            nova_pos[0] = max(0, min(nova_pos[0], H - 1))
            nova_pos[1] = nova_pos[1] % W

        return nova_pos