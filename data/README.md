# Data Pipeline — Lunar Ice Intelligence

## Estrutura

- raw/ → dados originais (NASA LRO)
- interim/ → dados limpos e alinhados
- processed/ → dados prontos para ML
  - lro/ → dados reais processados (validação)
    - mock/ → dados sintéticos para testes rápidos

## Pipeline

1. Baixar dados reais (download_diviner.py, outros scripts de ingestão)
2. Gerar dados sintéticos (generate_mock_data.py)
3. Limpar dados (clean_nasa_data.py)
4. Processar dataset (process_nasa_data.py)

## Outputs

- temperatura.npy
- insolacao.npy
- imagens/
- metadata.npy

### Observação

- `processed/lro/` → contém os dados reais para validação do modelo.
- `processed/lro/mock/` → contém dados sintéticos fisicamente plausíveis, usados para testes rápidos sem depender de ingestão externa.
- O `LunarDataset` aceita `mode="real"` ou `mode="mock"` para alternar entre as duas fontes.
