from model.hybrid_model import modelo_hibrido


def simular_movimento(pos, direcao, H=180, W=360):
    nova_pos = pos.copy()
    if direcao == "N": nova_pos[0] += 1
    elif direcao == "S": nova_pos[0] -= 1
    elif direcao == "E": nova_pos[1] += 1
    elif direcao == "W": nova_pos[1] -= 1
    nova_pos[0] = max(0, min(nova_pos[0], H - 1))
    nova_pos[1] = nova_pos[1] % W
    return nova_pos


def escolher_movimento(rover, ambiente):
    direcoes = ["N", "S", "E", "W"]
    melhor = None
    melhor_score = -float("inf")

    H, W = (ambiente._arr_insol.shape if ambiente._arr_insol is not None else (180, 360))

    for d in direcoes:
        nova_pos = simular_movimento(rover.pos, d, H=H, W=W)
        imagem, insolacao = ambiente.get_dados(nova_pos)

        # lat real da posição avaliada (índice grid → graus)
        lat_graus = float(nova_pos[0] - 90)

        # modelo recebe lat correto — essencial pois latitude é feature treinada
        score_modelo = modelo_hibrido(imagem, insolacao, lat=lat_graus)
        custo = ambiente.get_custo(nova_pos)

        score = score_modelo - custo

        if score > melhor_score:
            melhor_score = score
            melhor = d

    return melhor
