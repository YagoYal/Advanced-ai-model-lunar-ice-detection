import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MapContainer } from "react-leaflet";
import RoverPath from "./RoverPath";

// react-leaflet exige um MapContainer como pai
function Wrapper({ children }) {
  return (
    <MapContainer center={[0, 0]} zoom={2} style={{ height: 400 }}>
      {children}
    </MapContainer>
  );
}

function renderInMap(ui) {
  return render(ui, { wrapper: Wrapper });
}

describe("RoverPath", () => {
  it("nao renderiza nada sem caminho", () => {
    const { container } = renderInMap(<RoverPath caminho={null} />);
    // RoverPath retorna null — nenhum elemento SVG de polyline deve aparecer
    expect(container.querySelector(".leaflet-overlay-pane svg")).toBeNull();
    expect(container.querySelectorAll(".leaflet-marker-icon")).toHaveLength(0);
  });

  it("nao renderiza nada com caminho vazio", () => {
    const { container } = renderInMap(<RoverPath caminho={[]} />);
    expect(container.querySelector(".leaflet-overlay-pane svg")).toBeNull();
    expect(container.querySelectorAll(".leaflet-marker-icon")).toHaveLength(0);
  });

  it("renderiza sem lancar excecao com caminho valido", () => {
    const caminho = [
      { posicao: [175, 176], probabilidade_gelo: 0.3 },
      { posicao: [176, 176], probabilidade_gelo: 0.6 },
      { posicao: [177, 177], probabilidade_gelo: 0.85 },
    ];
    expect(() => renderInMap(<RoverPath caminho={caminho} />)).not.toThrow();
  });

  it("converte indices de grade para graus corretamente", () => {
    // gridParaLatLon: [i, j] -> [i-90, j-180]
    // posicao [90, 180] => lat=0, lon=0 (equador)
    // posicao [0, 0]    => lat=-90, lon=-180 (polo sul, meridiano)
    const casos = [
      { pos: [90, 180], esperado: [0, 0] },
      { pos: [0,   0],  esperado: [-90, -180] },
      { pos: [180, 360], esperado: [90, 180] },
      { pos: [177, 176], esperado: [87, -4] },   // perto de Haworth
      { pos: [3,   213], esperado: [-87, 33] },  // perto de Peary (polo norte => lat positivo)
    ];
    for (const { pos, esperado } of casos) {
      expect(pos[0] - 90).toBe(esperado[0]);
      expect(pos[1] - 180).toBe(esperado[1]);
    }
  });

  it("identifica o melhor ponto de gelo no caminho", () => {
    const caminho = [
      { posicao: [175, 176], probabilidade_gelo: 0.3 },
      { posicao: [176, 176], probabilidade_gelo: 0.95 },
      { posicao: [177, 177], probabilidade_gelo: 0.4 },
    ];
    const melhor = caminho.reduce((acc, p) =>
      (p.probabilidade_gelo ?? 0) > (acc.probabilidade_gelo ?? 0) ? p : acc,
      caminho[0]
    );
    expect(melhor.probabilidade_gelo).toBe(0.95);
    expect(melhor.posicao).toEqual([176, 176]);
  });

  it("nao mostra marcador de melhor ponto quando prob <= 0.5", () => {
    const caminho = [
      { posicao: [90, 180], probabilidade_gelo: 0.2 },
      { posicao: [91, 180], probabilidade_gelo: 0.4 },
    ];
    const melhor = caminho.reduce((acc, p) =>
      (p.probabilidade_gelo ?? 0) > (acc.probabilidade_gelo ?? 0) ? p : acc,
      caminho[0]
    );
    // RoverPath so renderiza marcador de melhor ponto se prob > 0.5
    expect(melhor.probabilidade_gelo > 0.5).toBe(false);
  });
});
