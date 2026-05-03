import { describe, it, expect, vi, beforeEach } from "vitest";
import { analisar, simular, analisarComMapa } from "./api";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("analisar", () => {
  it("retorna probabilidade_gelo ao receber resposta ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          probabilidade_gelo: 0.72,
          temperatura: 180.5,
          insolacao: 0.45,
        }),
      })
    );

    const data = await analisar(10, 10);
    expect(data.probabilidade_gelo).toBe(0.72);
  });

  it("lança erro quando a API retorna status de erro", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Posição inválida" }),
      })
    );

    await expect(analisar(9999, 9999)).rejects.toThrow("Posição inválida");
  });
});

describe("simular", () => {
  it("retorna caminho com movimentos do rover", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          inicio: [5, 5],
          caminho: [
            { movimento: "N", posicao: [6, 5], probabilidade_gelo: 0.5 },
            { movimento: "E", posicao: [6, 6], probabilidade_gelo: 0.6 },
          ],
        }),
      })
    );

    const data = await simular(5, 5, 2);
    expect(data.caminho).toHaveLength(2);
    expect(data.caminho[0].movimento).toBe("N");
  });

  it("lanca erro quando a API retorna status de erro", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: "Erro interno" }),
      })
    );
    await expect(simular(0, 0, 5)).rejects.toThrow("Erro interno");
  });

  it("cada passo do caminho tem posicao e probabilidade_gelo", async () => {
    const mockCaminho = [
      { movimento: "N", posicao: [6, 5], probabilidade_gelo: 0.72 },
      { movimento: "E", posicao: [6, 6], probabilidade_gelo: 0.81 },
      { movimento: "N", posicao: [7, 6], probabilidade_gelo: 0.55 },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ inicio: [5, 5], caminho: mockCaminho }),
      })
    );
    const data = await simular(5, 5, 3);
    for (const passo of data.caminho) {
      expect(passo).toHaveProperty("posicao");
      expect(passo).toHaveProperty("probabilidade_gelo");
      expect(Array.isArray(passo.posicao)).toBe(true);
      expect(passo.posicao).toHaveLength(2);
    }
  });
});

describe("analisarComMapa", () => {
  it("retorna probabilidade_gelo e mapa de calor", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          probabilidade_gelo: 0.88,
          heatmap: [[0.1, 0.9], [0.5, 0.3]],
        }),
      })
    );
    const data = await analisarComMapa(10, 10);
    expect(data.probabilidade_gelo).toBe(0.88);
    expect(data.heatmap).toBeDefined();
  });

  it("lanca erro em falha de rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
    await expect(analisarComMapa(0, 0)).rejects.toThrow("Network error");
  });
});
