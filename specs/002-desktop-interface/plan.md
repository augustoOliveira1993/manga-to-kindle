# Plano de Implementação: F002 — Interface Desktop

**Branch**: `002-desktop-interface` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo, contexto e constituição

Entregar shell PySide6 responsivo em PT-BR com Biblioteca, Adicionar mangá, Downloads, Conversão e Configurações, navegação por teclado, temas e estados de demonstração explicitamente simulados. Depende dos contratos e da configuração local de F001. Zero rede, arquivo convertido ou transferência real.

Conforme I–V: UI separada do domínio; operação demo em worker/fake clock; progresso/cancelamento por sinais; tema persistido por porta injetada; acessibilidade em ambos os temas; README explica limitações. A interação deve responder ≤200 ms, conforme a spec.

## Arquitetura e componentes

`presentation.qt` implementa `MainWindow`, navegação, páginas, estados, diálogos, tema e modelos Qt. `application` expõe casos de uso para carregar biblioteca, validar formato/esquema de URL sem envio, controlar demo e salvar tema. Fixtures são marcadas com `simulated=true` e banner; nunca são dados de provider real. Portas não importam Widgets. A navegação troca página sem perder seleção/operation state; controller de worker aceita cancelamento e envia estados por sinais.

Páginas: Biblioteca (vazia/lista demo), Adicionar (URL/estados), Downloads (fila demo), Conversão (seleção/pasta/perfil/formato demo) e Configurações (tema). Seleção usa IDs F001, não índice. Tema claro é o default. QFileDialog escolhe pasta, mas nenhuma escrita ocorre. Perfil/formato não afirma compatibilidade real.

## Acessibilidade, erros e estrutura

Tab order previsível, rótulos acessíveis PT-BR, foco visível, setas para navegar, Espaço seleciona, Enter/Espaço ativa conforme widget. Texto/ícone além de cor comunicam status. Validação não ecoa URL. Erros corrigíveis oferecem nova tentativa, edição ou cancelamento. Widgets só são alterados em thread UI.

```text
src/manga_to_kindle/presentation/qt/{main_window,navigation,pages,components,theme,view_models,workers}/
src/manga_to_kindle/application/ui/{load_library,validate_url,demo_operation,save_theme}.py
tests/{unit,ui,acceptance}/desktop/
```

## Testes e rastreabilidade

Qt offscreen: navegação, estados, teclado, multi-seleção, pasta/perfil/formato, tema após 2 reinícios, progresso/cancelamento, labels demo e proibição de rede/arquivo. Uma operação simulada de 30 s usa fake clock/sinais, medindo interação ≤200 ms. Mapear RF-001–016, RNF-001–006 e CS-001–005 para as verificações acima. Nenhuma suíte foi executada.

Risco: indicação de demo se perder em página secundária; aplicar componente persistente comum e teste por view. Risco: teste de desempenho frágil por carga; estabelecer perfil de referência Qt/Windows, sem alterar limite especificado.

## Dependências e artefatos

F001 fornece aplicação, config, lifecycle, tipos e SQLite. F003/F004 ainda não entram; URL não consulta serviço. Versão PySide6 fica pendente de compatibilidade em ambiente resolvido. Contrato e estados em [contracts/ui-boundary.md](contracts/ui-boundary.md) / [data-model.md](data-model.md); [research.md](research.md), [quickstart.md](quickstart.md) orientam validação.
