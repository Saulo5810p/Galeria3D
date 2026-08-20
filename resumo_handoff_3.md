# Player3D (ex-Galeria3D) — resumo de handoff #3

Cole este arquivo inteiro, junto com o `Player3D_contexto.md` original (que
continua valendo como especificação-mãe de todos os passos), no início do
próximo chat. Os `resumo_handoff.md` e `resumo_handoff_2.md` anteriores já
estão incorporados aqui — não precisa colar os três, só este.

Repositório: https://github.com/Saulo5810p/Galeria3D — o Claude clona
direto de lá.

## Checklist da ordem de execução (do contexto original)

- [x] Passo 0 — Limpeza
- [x] Passo 1 — Fonte de dados vídeo→áudio
- [x] Passo 2 — Grade principal
- [x] Passo 3 — Clique abre reprodução (sem mudança de código, ver handoff #2)
- [x] **Passo 4.1** — Tela de reprodução: conectar `MoviePlayer.java` ao
      `MusicPlaybackService` (bindService, VideoView→ImageView+MediaPlayer)
- [x] **Passo 4.2** — Tela de reprodução: 4 botões novos (Repetir todas,
      Anterior, Próxima, Repetir uma)
- [ ] Passo 4.3 — Botão do editor de fotos na tela de reprodução
- [ ] Passo 5 — Filtros
- [ ] Passo 6 — Busca
- [ ] Passo 7 — Mover/criar álbum
- [ ] Passo 8 — Widget
- [x] Passo 9 — Service + notificação (feito fora de ordem, como o próprio
      contexto original manda)

Ao final de cada passo, compilar antes de avançar. Se falhar, corrigir só
o erro apontado, sem sair do escopo do passo atual.

## Passo 4.1 — o que foi feito

`MoviePlayer.java` parou de instanciar `VideoView`/`MediaPlayer` direto.
Agora faz `bindService()` no `MusicPlaybackService` (Passo 9) e implementa
`MusicPlaybackService.Callback` (estado de reprodução/erro) e
`MusicPlaybackService.QueueController` (próxima/anterior, comportamento
mínimo por enquanto — ver "Pendência: fila real" abaixo). O layout
`movie_view.xml` trocou `<VideoView>` por `<ImageView>` (capa da faixa,
extraída do próprio `Uri` via `MediaMetadataRetriever`, mesma técnica do
Passo 1.5). Feature `Virtualizer` (efeito de áudio) foi removida — dependia
do `audioSessionId` do `MediaPlayer`, que não está exposto na API pública
do Service.

**Bug corrigido depois do Passo 4.1:** app crashava ao abrir uma faixa
(`SecurityException: startForeground ... requires FOREGROUND_SERVICE`).
Faltavam `<uses-permission>` de `FOREGROUND_SERVICE` e
`FOREGROUND_SERVICE_MEDIA_PLAYBACK` no manifest (lacuna do Passo 9, exigida
desde Android 9/14). Corrigido com `passo9_hotfix_foreground_permission.py`.

## Passo 4.2 — o que foi feito

4 botões novos na tela de reprodução, construídos com o MESMO padrão
programático do botão de play/pause já existente (`ImageView` +
`bg_vidcontrol` de fundo + `ScaleType.CENTER`), na ordem **[Repetir
todas] [Anterior] [Play/Pause] [Próxima] [Repetir uma]** — idêntica à
ordem já testada na notificação (Passo 9), mesma fonte de verdade.

- Os botões ficam **só em `MovieControllerOverlay.java`**, não em
  `CommonControllerOverlay.java` (compartilhada com `TrimControllerOverlay`,
  a tela de corte de vídeo) — não faz sentido repeat/anterior/próxima numa
  tela de corte, que já está fora do escopo de qualquer passo.
- `ControllerOverlay.Listener` ganhou 4 métodos novos
  (`onPrevious`/`onNext`/`onToggleRepeatAll`/`onToggleRepeatOne`), o que
  obrigou a adicionar 4 stubs vazios em `TrimVideo.java` (só para compilar
  — corte de vídeo não usa isso).
- Anterior/Próxima mandam o MESMO `Intent` (`ACTION_PREVIOUS`/
  `ACTION_NEXT`) que a notificação já manda — reaproveita a lógica de
  limiar de 3s já testada em `MusicPlaybackService.requestPrevious()` em
  vez de duplicá-la na tela.
- Ícones: os 4 PNGs de `drawable-nodpi` (Passo 9) foram apagados e
  viraram vetores XML em `drawable/` (mesma paleta cinza `#D6D6D6`),
  com uma segunda versão `_active` (cor de destaque
  `@color/holo_blue_light`) trocada quando o modo de repeat respectivo
  está ligado.
  **Trade-off sinalizado:** o ícone "Repetir todas" original tinha a
  palavra "ALL" desenhada. Vetor com texto legível em ~48dp não é viável
  à mão sem ferramenta de design (ficaria ilegível de qualquer forma
  nesse tamanho). Ficou como ícone de loop puro (sem texto); "Repetir
  uma" mantém o loop + dígito "1" (que continua legível pequeno). A
  diferença entre os dois fica clara pelo par de ícones + cor de
  destaque quando ativo — mas não é pixel-idêntico ao PNG original.

## Correção de aberturas externas (fora da lista de passos, pedido direto)

O app aparecia como opção de "Abrir com..."/"Escolher..." pra IMAGENS em
outros apps (galeria padrão do sistema, picker de fotos). Corrigido no
`AndroidManifest.xml`:

- `MovieActivity`: filtro de `rtsp`/mimetypes de vídeo removido, trocado
  por mimetypes de áudio (mp3/mp4a/ogg/wav/flac/aac). Filtro de playlist
  HTTP live (`audio/mpegurl`) mantido, já era de áudio.
- `GalleryActivity`: categoria `APP_GALLERY` removida (deixa de se
  registrar como Galeria padrão do sistema). Filtros `GET_CONTENT`/`PICK`/
  `VIEW` de imagem e vídeo (incluindo o par `VIEW`+`REVIEW` do fluxo de
  revisão da Câmera) removidos e trocados por `GET_CONTENT`/`PICK`/`VIEW`
  de áudio — agora o app aparece como opção pra abrir/escolher MÚSICA.

**Pendência sinalizada, não mexida:** o manifest ainda registra
`TrimVideo` (ação `TRIM`, `video/*`), `FilterShowActivity` (ação `EDIT`,
`image/*`) e `CropActivity` (ação `CROP`, `image/*`) como opções externas
de EDIÇÃO de foto/vídeo (menu "Editar com..."/"Cortar com..." de outros
apps — diferente do menu "Abrir com..." que a `GalleryActivity`
controlava). São subsistemas inteiros de edição de imagem
(`filtershow/`), já fora do escopo de qualquer passo até agora, do mesmo
jeito que `SecureAlbum.java` já estava sinalizado como pendência no
handoff #2. Não mexido — avisar explicitamente se quiser que isso também
seja removido.

## Pendências sinalizadas para as próximas sessões (ordem que o usuário pediu)

1. **Bug dos botões da notificação** — às vezes não respondem ao clique
   (pausar/avançar/retroceder), de forma inconsistente. Ainda não
   diagnosticado.
2. **Mini-player na tela principal** — uma seekbar com slider de tempo
   fora da tela de reprodução: um quadrado pequeno com a capa da música
   atual, botões mini de play/pause/próxima/anterior (reaproveitando os
   mesmos XMLs traduzidos dos ícones do Passo 4.2), que abre a tela de
   reprodução ao clicar. Ainda não existe no app.
3. Depois disso, seguir para o Passo 4.3 (botão do editor de fotos na
   tela de reprodução) e Passo 5 em diante.

## Pendência conhecida, não crítica (herdada do handoff #1)

`SecureAlbum.java` (feature de "câmera segura"/stitching, tela de
bloqueio) ainda consulta `MediaStore.Video` de verdade em vários pontos —
não crasha, não é escopo de nenhum passo até agora.

## Regras de obediência (seguem valendo, do contexto original)

Não inventar arquitetura, não criar telas paralelas, adaptar arquivos
existentes em vez de reescrever do zero, parar e perguntar quando a
instrução for genuinamente ambígua. Expansões de escopo pontuais e
mecânicas (ex.: criar um ícone/recurso que falta pra um passo funcionar de
verdade) são aceitáveis quando documentadas claramente — mas qualquer
coisa que pareça "nova arquitetura" ou avanço de passo futuro deve ser
sinalizada explicitamente antes de prosseguir.

## Lição de workflow (segue valendo, do contexto original)

Scripts de mais de ~50 linhas sempre viram arquivo `.py` de verdade
(ferramenta de criar arquivo + disponibilizar pra download), nunca texto
gigante colado no chat. Todo script de patch deve: conferir pré-requisitos
antes de mexer (falhar cedo, sem tocar em nada, se o projeto não estiver
no estado esperado); fazer backup antes de editar (fora da árvore `res/`);
usar substituição de texto com checagem de "exatamente 1 ocorrência"; ser
idempotente (rodar de novo não duplica nem corrompe nada — testar isso
explicitamente); terminar com uma verificação (grep) confirmando que não
sobrou resto do padrão antigo; ser validado no sandbox (rodar contra uma
cópia limpa do projeto, inclusive rodando 2-3x seguidas) antes de ser
entregue. **Lição nova desta sessão:** ao fazer backup de um arquivo
binário (ex.: PNG), usar modo binário (`rb`/`wb`), não texto UTF-8 — um
backup de PNG em modo texto quebra com `UnicodeDecodeError`.
