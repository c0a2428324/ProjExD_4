import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_w: (0, -1),
        pg.K_s: (0, +1),
        pg.K_a: (-1, 0),
        pg.K_d: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"     
        self.hyper_life = 0  
    
    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
    def update(self, key_lst: list[bool], screen: pg.Surface):
        # --- 追加機能1：高速化（左Shift押下中は速度20、通常は10） ---
        speed = 20 if key_lst[pg.K_LSHIFT] else 10

        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]

        self.rect.move_ip(speed*sum_mv[0], speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-speed*sum_mv[0], -speed*sum_mv[1])

        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        # --- 無敵状態の継続処理 ---
        if self.state == "hyper":
            self.hyper_life -= 1
            self.image = pg.transform.laplacian(self.image)
            if self.hyper_life <= 0:
                self.state = "normal"

        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active" 

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス（弾幕対応：angle0で回転発射）
    """
    def __init__(self, bird: Bird, angle0: float = 0):
        """
        引数 bird : ビームを放つこうかとん
        引数 angle0 : 追加回転角度（度）。0なら従来どおり。
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        base_angle = math.degrees(math.atan2(-self.vy, self.vx))
        angle = base_angle + angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    弾幕（複数ビーム発射）クラス
    """
    def __init__(self, bird: Bird, num: int = 5):
        self.bird = bird
        self.num = num

    def gen_beams(self) -> list:
        """
        -50°～+50°の範囲でnum本のビームを生成しリストで返す
        0°を必ず含むように均等配置
        """
        if self.num == 1:
            angles = [0.0]
        else:
            angles = [-50 + 100*i/(self.num-1) for i in range(self.num)]
        return [Beam(self.bird, angle0=a) for a in angles]


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life
        self.rect

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  
        self.state = "down"  
        self.interval = random.randint(50, 300)  
        self.emp_affected = False  

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class EMP:
    """
    EMPに関するクラス
    """
    def __init__(self, enemies: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        self.enemies = enemies
        self.bombs = bombs
        self.screen = screen
        self.active = False
        self.effect_timer = 0
        
    def activate(self):
        """EMP効果を発動する"""
        # 敵機を無力化する
        for enemy in self.enemies:
            if not enemy.emp_affected: 
                enemy.interval = float('inf') 
                # ラプラシアンフィルターを適用する
                enemy.image = pg.transform.laplacian(enemy.image)
                enemy.emp_affected = True
        
        # 爆弾を無力化する
        for bomb in self.bombs:
            if bomb.state == "active":  
                bomb.speed /= 2  
                bomb.state = "inactive"  
        
        self.active = True
        self.effect_timer = 3  
    def update(self):
        """更新EMP效果"""
        if self.active:
            # 黄色半透明の矩形
            effect_surface = pg.Surface((WIDTH, HEIGHT))
            effect_surface.set_alpha(128)  
            effect_surface.fill((255, 255, 0)) 
            self.screen.blit(effect_surface, (0, 0))
            
            # 更新時間
            self.effect_timer -= 1
            if self.effect_timer <= 0:
                self.active = False


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


####追加####
class Gravity(pg.sprite.Sprite):
    """
    画面全体を覆う重力場に関するクラス
    """
    def __init__(self, life: int):
        """
        重力場Surfaceを生成する
        引数 life：発動時間
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(100) # 透明度
        self.rect = self.image.get_rect()
        self.life = life

    def update(self):
        """
        発動時間を1減算し、0未満になったらkillする
        """
        self.life -= 1
        if self.life < 0:
            self.kill()
        
class Shield(pg.sprite.Sprite):
    """
    シールドに関するクラス
    """
    def __init__(self,bird: Bird,life: int):
        """
        シールドSurfaceを生成する
        引数1 bird: こうかとん
        引数2 life: 消滅時間
        """
        super().__init__()
        self.life = life
        self.image = pg.Surface((20, bird.rect.height * 2))
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, 20, bird.rect.height * 2))
        vx, vy = bird.dire
        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotozoom(self.image, angle, 1.0)
        self.rect = self.image.get_rect()
        self.image.set_colorkey((0, 0, 0))
        self.rect.centerx = bird.rect.centerx + bird.rect.width * vx
        self.rect.centery = bird.rect.centery + bird.rect.height * vy

    def update(self):
        """
        壁の消滅時間
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    shield = pg.sprite.Group()

    ####追加####
    gravity = pg.sprite.Group()
    # EMP実例
    emp = EMP(emys, bombs, screen)

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            # --- Space：発射 / Shift+Space：弾幕発射 ---
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:
                    neo = NeoBeam(bird, num=5)  # 本数は必要に応じて変更OK
                    for b in neo.gen_beams():
                        beams.add(b)
                else:
                    beams.add(Beam(bird))

            ####追加####
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value >= 200:
                    gravity.add(Gravity(400))
                    score.value -= 200

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                # EMPの発動条件を追加する
                if event.key == pg.K_e and score.value > 20:
                    emp.activate()
                    score.value -= 20  # スコアを消費する
            
            if event.type == pg.KEYDOWN and event.key == pg.K_r:
                if score.value >= 50 and not shield:
                    score.value -= 50
                    shield.add(Shield(bird, 400))
        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for bomb in pg.sprite.groupcollide(bombs, shield, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

            
            # --- 無敵状態の発動 ---
        if key_lst[pg.K_RSHIFT] and bird.state == "normal" and score.value >= 100:
            bird.state = "hyper"
            bird.hyper_life = 500
            score.value -= 100  # スコア消費
            beams.add(Beam(bird))


        # --- こうかとんと爆弾の衝突処理 ---
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))  # 爆弾だけ爆発
                score.value += 1               # スコア+1
            elif bomb.state == "active":  # 
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        # ビームと敵機の衝突判定
        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        # ビームと爆弾の衝突判定（EMP影响済みの爆弾は除く）
        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            if bomb.state == "active":  # 
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1  # 1点アップ
            else:
                # EMP影響下の爆弾は被弾すると即時消滅し、爆発効果を発生しない
                pass

        
        ####追加####  
        for g in gravity:
            for bomb in pg.sprite.spritecollide(g, bombs, True):
                exps.add(Explosion(bomb, 50))
                score.value += 1
            for emy in pg.sprite.spritecollide(g, emys, True):
                exps.add(Explosion(emy, 100))
                score.value += 10

        #bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        #exps.update()
        #exps.draw(screen)

        ####追加####
        gravity.update()
        gravity.draw(screen)

        ####場所変更####
        exps.update()
        exps.draw(screen)
        bird.update(key_lst, screen)

        
        # 更新EMP效果
        emp.update()
        
        shield.update()
        shield.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)
        

if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()