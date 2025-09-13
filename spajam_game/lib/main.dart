import 'package:flame/components.dart';
import 'package:flame/game.dart';
import 'package:flutter/material.dart'; // 色を指定するために必要

void main() {
  final game = MyGame();
  runApp(GameWidget(game: game));
}

class MyGame extends FlameGame {
  // ゲームのロード時に一度だけ呼ばれるメソッド
  @override
  Future<void> onLoad() async {
    await super.onLoad(); // 必須

    // TextComponent を作成
    final style = TextStyle(
      color: Colors.white, // 文字の色
      fontSize: 48.0,      // 文字のサイズ
    );
    final textRenderer = TextPaint(style: style);

    final myText = TextComponent(
      text: 'Hello, Flame!', // 表示したい文字列
      textRenderer: textRenderer,
      position: Vector2(50, 100), // 表示する位置 (x, y)
    );

    // 作成したコンポーネントをゲームに追加
    add(myText);
  }
}