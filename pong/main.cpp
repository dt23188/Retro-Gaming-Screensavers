#include "raylib.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <random>
#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#ifdef _WIN32
// Declare only the APIs needed here to avoid Windows/raylib name collisions.
extern "C" __declspec(dllimport) int __stdcall MoveFileExW(const wchar_t*, const wchar_t*, unsigned long);
extern "C" __declspec(dllimport) unsigned long __stdcall GetLastError();
#endif

namespace {
constexpr int kScreenWidth = 1280;
constexpr int kScreenHeight = 720;
constexpr float kPaddleWidth = 22.0F;
constexpr float kPaddleHeight = 122.0F;
constexpr float kPaddleSpeed = 620.0F;
constexpr float kBallRadius = 13.0F;
constexpr int kWinningScore = 7;
constexpr int kParticleCount = 160;
constexpr float kSpeedIncreaseInterval = 15.0F;
constexpr float kSpeedIncrease = 48.0F;
constexpr float kFireTrailLifetime = 0.38F;
constexpr Color kFireRed{255, 46, 8, 255};
constexpr Color kFireOrange{255, 126, 12, 255};
constexpr Color kFireYellow{255, 226, 100, 255};

constexpr Color kInk{225, 242, 255, 255};
constexpr Color kMuted{103, 137, 166, 255};
constexpr Color kBlue{42, 213, 255, 255};
constexpr Color kPink{255, 64, 160, 255};
constexpr Color kGold{255, 215, 92, 255};
constexpr Color kBackground{0, 0, 0, 255};

enum class Scene { Title, Playing, GameOver };
enum class Mode { Solo, Versus, AiVersusAi };

struct Paddle { Rectangle rect{}; float velocity{}; float recoilTime{}; float recoilDirection{}; };
struct Ball {
    Vector2 position{};
    Vector2 velocity{};
    float speed{480.0F};
    bool waiting{true};
};
struct Particle {
    Vector2 position{};
    Vector2 velocity{};
    Color color{};
    float life{};
    float maximumLife{1.0F};
    float radius{};
};
struct TrailPoint { Vector2 position{}; float age{}; };

float Clamp01(float value) { return std::clamp(value, 0.0F, 1.0F); }
Color FadeColor(Color color, float alpha) {
    color.a = static_cast<unsigned char>(255.0F * Clamp01(alpha));
    return color;
}

class PongGame {
public:
    PongGame(bool screensaver, bool preview, bool ai, int monitor, float duration, bool lockFrames = false, int width = kScreenWidth, int height = kScreenHeight, float teamHue = -1)
        : random_(std::random_device{}()), screensaver_(screensaver), preview_(preview), duration_(duration) {
        if (teamHue >= 0) {
            teamColors_[0] = ColorFromHSV(teamHue, .78F, 1.0F);
            teamColors_[1] = ColorFromHSV(std::fmod(teamHue + 180.0F, 360.0F), .78F, 1.0F);
        }
        SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT | FLAG_MSAA_4X_HINT | (lockFrames ? FLAG_WINDOW_HIDDEN : 0));
        InitWindow(width, height, lockFrames ? "omarchy-pong-lock-renderer" : screensaver && !preview ? "org.omarchy.screensaver" : "Neon Pong");
        if (screensaver && !preview) {
            monitor = std::clamp(monitor, 0, GetMonitorCount() - 1);
            SetWindowMonitor(monitor);
            const Vector2 position = GetMonitorPosition(monitor);
            SetWindowPosition(static_cast<int>(position.x), static_cast<int>(position.y));
            SetWindowSize(GetMonitorWidth(monitor), GetMonitorHeight(monitor));
            SetWindowState(FLAG_WINDOW_UNDECORATED);
            HideCursor();
        }
        SetExitKey(KEY_NULL);
        if (!lockFrames) SetWindowMinSize(320, 240);
        if (!screensaver) InitAudioDevice();
        SetTargetFPS(screensaver ? 60 : 144);
        createSounds();
        resizeArena(GetScreenWidth(), GetScreenHeight());
        resetMatch();
        if (screensaver || ai) startMatch(Mode::AiVersusAi);
    }
    ~PongGame() {
        if (audioReady_) {
            UnloadSound(paddleSound_);
            UnloadSound(wallSound_);
            UnloadSound(scoreSound_);
            CloseAudioDevice();
        }
        CloseWindow();
    }
    void run() {
        while (!WindowShouldClose()) {
            const float dt = GetFrameTime();
            elapsed_ += dt;
            if (duration_ > 0 && elapsed_ >= duration_) break;
            if (screensaver_) {
                if (IsKeyPressed(KEY_ESCAPE)) break;
                if (!preview_ && (GetKeyPressed() != 0 || IsMouseButtonPressed(MOUSE_BUTTON_LEFT) ||
                    IsMouseButtonPressed(MOUSE_BUTTON_RIGHT) || IsMouseButtonPressed(MOUSE_BUTTON_MIDDLE) ||
                    GetMouseWheelMove() != 0 || (elapsed_ > 1.0F && Vector2Moved()))) break;
            } else if (scene_ == Scene::Title && IsKeyPressed(KEY_ESCAPE)) break;
            advanceRealtime(dt);
            draw();
        }
    }

    void runLockFrames(const std::string& output) {
        const int width = GetScreenWidth(), height = GetScreenHeight();
        RenderTexture2D target = LoadRenderTexture(width, height);
        if (!IsRenderTextureReady(target)) throw std::runtime_error("Cannot create lock renderer");
        double last = GetTime(), start = last;
        const bool bitmap = std::filesystem::path(output).extension() == ".bmp";
        const std::string temporary = output + (bitmap ? ".tmp.bmp" : ".tmp.png");
        while (duration_ <= 0 || GetTime() - start < duration_) {
            const double frameStart = GetTime();
            const float dt = static_cast<float>(frameStart - last);
            last = frameStart;
            PollInputEvents();
            advanceRealtime(dt);
            BeginTextureMode(target);
            ClearBackground(kBackground);
            const float arenaScale = std::min(width, height) / 720.0F;
            const Vector2 shake = cameraShake();
            BeginMode2D({{shake.x * arenaScale, shake.y * arenaScale}, {0, 0}, 0, arenaScale});
            drawArena();
            EndMode2D();
            const float scale = std::min(width / 1280.0F, height / 720.0F);
            BeginMode2D({{(width - 1280 * scale) * 0.5F + shake.x * arenaScale * 0.35F,
                          (height - 720 * scale) * 0.5F + shake.y * arenaScale * 0.35F}, {0, 0}, 0, scale});
            if (scene_ == Scene::GameOver) drawGameOver();
            else if (showMatchHud()) drawMatchHud();
            EndMode2D();
            EndTextureMode();
            Image frame = LoadImageFromTexture(target.texture);
            ImageFlipVertical(&frame);
            const bool exported = ExportImage(frame, temporary.c_str());
            UnloadImage(frame);
            if (!exported) throw std::runtime_error("Cannot export lock frame");
#ifdef _WIN32
            const auto source = std::filesystem::path(temporary).wstring();
            const auto destination = std::filesystem::path(output).wstring();
            bool replaced = false;
            for (int attempt = 0; attempt < 25; ++attempt) {
                if (MoveFileExW(source.c_str(), destination.c_str(), 1 /* MOVEFILE_REPLACE_EXISTING */)) {
                    replaced = true;
                    break;
                }
                const auto error = GetLastError();
                if (error != 5 && error != 32 && error != 33)
                    throw std::runtime_error("Cannot replace lock frame: " + std::to_string(error));
                WaitTime(0.002);
            }
            // A reader may briefly hold the image open. Keep the previous frame
            // and retry with the next rendered image instead of stopping Pong.
            if (!replaced) continue;
#else
            if (std::rename(temporary.c_str(), output.c_str()) != 0)
                throw std::runtime_error("Cannot write lock frame");
#endif
            std::cout << "frame" << std::endl;
            WaitTime(std::max(0.0, 1.0 / (bitmap ? 60.0 : 24.0) - (GetTime() - frameStart)));
        }
        UnloadRenderTexture(target);
    }

private:
    // Preserve elapsed time while keeping collision and AI updates small.
    void advanceRealtime(float elapsed) {
        double remaining = std::max(0.0, static_cast<double>(elapsed));
        while (remaining > 0.0) {
            const double step = std::min(remaining, 1.0 / 120.0);
            update(static_cast<float>(step));
            remaining -= step;
        }
    }
    bool Vector2Moved() const {
        const Vector2 delta = GetMouseDelta();
        return delta.x != 0 || delta.y != 0;
    }
    void createSounds() {
        if (!IsAudioDeviceReady()) return;
        paddleSound_ = makeTone(640.0F, 0.07F, 0.22F);
        wallSound_ = makeTone(360.0F, 0.045F, 0.14F);
        scoreSound_ = makeTone(170.0F, 0.25F, 0.24F);
        audioReady_ = true;
    }
    Sound makeTone(float frequency, float duration, float volume) {
        constexpr unsigned int sampleRate = 44100;
        const unsigned int count = static_cast<unsigned int>(sampleRate * duration);
        std::vector<short> samples(count);
        for (unsigned int i = 0; i < count; ++i) {
            const float t = static_cast<float>(i) / sampleRate;
            const float envelope = 1.0F - static_cast<float>(i) / count;
            samples[i] = static_cast<short>(std::sin(2.0F * PI * frequency * t) *
                                            envelope * volume * 32767.0F);
        }
        Wave wave{count, sampleRate, 16, 1, samples.data()};
        return LoadSoundFromWave(wave);
    }

    void update(float dt) {
        resizeArena(GetScreenWidth(), GetScreenHeight());
        if (!screensaver_ && IsKeyPressed(KEY_F11)) ToggleBorderlessWindowed();
        pulse_ += dt;
        updateImpactEffects(dt);
        updateParticles(dt);
        updateTrail(dt);
        if (!screensaver_ && IsKeyPressed(KEY_M)) muted_ = !muted_;
        if (scene_ == Scene::Title) {
            if (IsKeyPressed(KEY_ONE) || IsKeyPressed(KEY_ENTER)) startMatch(Mode::Solo);
            if (IsKeyPressed(KEY_TWO)) startMatch(Mode::Versus);
            if (IsKeyPressed(KEY_THREE)) startMatch(Mode::AiVersusAi);
            return;
        }
        if (scene_ == Scene::GameOver) {
            if (mode_ == Mode::AiVersusAi) {
                rematchTimer_ -= dt;
                if (rematchTimer_ <= 0) startMatch(mode_);
            }
            if (IsKeyPressed(KEY_ENTER) || IsKeyPressed(KEY_R)) startMatch(mode_);
            if (IsKeyPressed(KEY_ESCAPE)) scene_ = Scene::Title;
            return;
        }
        if (!screensaver_ && (IsKeyPressed(KEY_ESCAPE) || IsKeyPressed(KEY_P))) paused_ = !paused_;
        if (!screensaver_ && IsKeyPressed(KEY_R)) startMatch(mode_);
        if (paused_) return;
        updatePaddles(dt);
        if (ball_.waiting) {
            serveTimer_ -= dt;
            if (serveTimer_ <= 0.0F || IsKeyPressed(KEY_SPACE)) launchBall();
            return;
        }
        updateDifficulty(dt);
        // Small physics steps keep fast balls from skipping paddle collisions.
        const float travel = std::hypot(ball_.velocity.x, ball_.velocity.y) * dt;
        const int steps = std::max(1, static_cast<int>(std::ceil(travel / kBallRadius)));
        for (int i = 0; i < steps && !ball_.waiting && scene_ == Scene::Playing; ++i)
            updateBall(dt / steps);
    }

    void updateDifficulty(float dt) {
        speedIncreaseTimer_ += dt;
        while (speedIncreaseTimer_ >= kSpeedIncreaseInterval) {
            speedIncreaseTimer_ -= kSpeedIncreaseInterval;
            speedBonus_ += kSpeedIncrease;
            const float previousSpeed = ball_.speed;
            ball_.speed += kSpeedIncrease;
            const float factor = ball_.speed / previousSpeed;
            ball_.velocity.x *= factor;
            ball_.velocity.y *= factor;
            flash_ = 1.0F;
        }
    }

    void updatePaddles(float dt) {
        const float leftInput = (IsKeyDown(KEY_S) ? 1.0F : 0.0F) -
                                (IsKeyDown(KEY_W) ? 1.0F : 0.0F);
        if (mode_ == Mode::AiVersusAi) updateAi(left_, true, dt);
        else movePaddle(left_, leftInput, dt);
        if (mode_ == Mode::Versus) {
            const float rightInput = (IsKeyDown(KEY_DOWN) ? 1.0F : 0.0F) -
                                     (IsKeyDown(KEY_UP) ? 1.0F : 0.0F);
            movePaddle(right_, rightInput, dt);
        } else {
            updateAi(right_, false, dt);
        }
    }
    void updateAi(Paddle& paddle, bool leftSide, float dt) {
        float target = (arenaTop_ + arenaBottom_) * 0.5F;
        if (!ball_.waiting && (leftSide ? ball_.velocity.x < 0 : ball_.velocity.x > 0))
            target = ball_.position.y + ball_.velocity.y * 0.075F;
        // Small, different aiming offsets keep autonomous rallies varied.
        if (mode_ == Mode::AiVersusAi)
            target += std::sin(pulse_ * (leftSide ? 1.7F : 1.3F)) * 34.0F;
        const float center = paddle.rect.y + paddle.rect.height * 0.5F;
        const float input = std::clamp((target - center) / 40.0F, -1.0F, 1.0F);
        movePaddle(paddle, input * 0.84F, dt);
    }

    void movePaddle(Paddle& paddle, float input, float dt) {
        paddle.velocity = input * kPaddleSpeed * worldHeight_ / kScreenHeight;
        paddle.rect.y = std::clamp(paddle.rect.y + paddle.velocity * dt,
                                   arenaTop_, arenaBottom_ - paddle.rect.height);
    }

    void updateBall(float dt) {
        trailTimer_ -= dt;
        if (trailTimer_ <= 0.0F) {
            trail_.push_back({ball_.position, 0.0F});
            trailTimer_ = 0.008F;
        }
        ball_.position.x += ball_.velocity.x * dt;
        ball_.position.y += ball_.velocity.y * dt;
        if (ball_.position.y - kBallRadius <= arenaTop_ && ball_.velocity.y < 0.0F) {
            ball_.position.y = arenaTop_ + kBallRadius;
            ball_.velocity.y *= -1.0F;
            wallImpact({ball_.position.x, arenaTop_});
        } else if (ball_.position.y + kBallRadius >= arenaBottom_ && ball_.velocity.y > 0.0F) {
            ball_.position.y = arenaBottom_ - kBallRadius;
            ball_.velocity.y *= -1.0F;
            wallImpact({ball_.position.x, arenaBottom_});
        }
        collidePaddle(left_, true);
        collidePaddle(right_, false);
        if (ball_.position.x < arenaLeft_ - kBallRadius) scorePoint(1);
        if (ball_.position.x > arenaRight_ + kBallRadius) scorePoint(0);
    }
    void collidePaddle(Paddle& paddle, bool leftSide) {
        if ((leftSide && ball_.velocity.x >= 0.0F) || (!leftSide && ball_.velocity.x <= 0.0F)) return;
        const Rectangle expanded{paddle.rect.x - kBallRadius, paddle.rect.y - kBallRadius,
                                 paddle.rect.width + kBallRadius * 2.0F,
                                 paddle.rect.height + kBallRadius * 2.0F};
        if (!CheckCollisionPointRec(ball_.position, expanded)) return;
        const float center = paddle.rect.y + paddle.rect.height * 0.5F;
        const float offset = std::clamp((ball_.position.y - center) /
                                        (paddle.rect.height * 0.5F), -1.0F, 1.0F);
        ball_.speed = std::min(ball_.speed * 1.055F, 920.0F + speedBonus_);
        const float angle = offset * 1.02F;
        ball_.velocity = {std::cos(angle) * ball_.speed * (leftSide ? 1.0F : -1.0F),
                          std::sin(angle) * ball_.speed + paddle.velocity * 0.16F};
        ball_.position.x = leftSide ? paddle.rect.x + paddle.rect.width + kBallRadius
                                    : paddle.rect.x - kBallRadius;
        ++rally_;
        triggerShake(16.0F + std::min(speedBonus_ * 0.025F, 8.0F), 0.30F);
        paddle.recoilTime = 0.32F;
        paddle.recoilDirection = leftSide ? -1.0F : 1.0F;
        flash_ = 1.0F;
        spawnBurst(ball_.position, leftSide ? teamColors_[0] : teamColors_[1], 18);
        play(paddleSound_);
    }
    void wallImpact(Vector2 position) {
        triggerShake(12.0F + std::min(speedBonus_ * 0.02F, 6.0F), 0.24F);
        spawnBurst(position, kGold, 7);
        play(wallSound_);
    }
    void scorePoint(int player) {
        ++scores_[player];
        spawnBurst(ball_.position, player == 0 ? teamColors_[0] : teamColors_[1], 46);
        triggerShake(34.0F, 0.65F);
        left_.recoilTime = right_.recoilTime = 0.32F;
        left_.recoilDirection = -1.0F;
        right_.recoilDirection = 1.0F;
        play(scoreSound_);
        if (scores_[player] >= kWinningScore) {
            winner_ = player;
            rematchTimer_ = 3.0F;
            scene_ = Scene::GameOver;
            return;
        }
        resetRound(player == 0 ? 1 : -1);
    }
    void resetRound(int direction) {
        ball_.position = {(arenaLeft_ + arenaRight_) * 0.5F, (arenaTop_ + arenaBottom_) * 0.5F};
        ball_.velocity = {static_cast<float>(direction), 0.0F};
        ball_.speed = 480.0F + speedBonus_;
        ball_.waiting = true;
        serveDirection_ = direction;
        serveTimer_ = mode_ == Mode::AiVersusAi ? 2.0F : 1.25F;
        rally_ = 0;
        trail_.clear();
        trailTimer_ = 0.0F;
    }
    void launchBall() {
        std::uniform_real_distribution<float> angle(-0.52F, 0.52F);
        const float value = angle(random_);
        ball_.velocity = {std::cos(value) * ball_.speed * serveDirection_,
                          std::sin(value) * ball_.speed};
        ball_.waiting = false;
    }
    void resetMatch() {
        shake_ = shakeTime_ = 0.0F;
        left_.recoilTime = right_.recoilTime = 0.0F;
        left_.velocity = right_.velocity = 0.0F;
        speedIncreaseTimer_ = 0.0F;
        speedBonus_ = 0.0F;
        scores_ = {0, 0};
        particles_ = {};
        const float paddleHeight = worldHeight_ * (kPaddleHeight / kScreenHeight);
        left_.rect = {32.0F, (worldHeight_ - paddleHeight) * 0.5F, kPaddleWidth, paddleHeight};
        right_.rect = {worldWidth_ - 32.0F - kPaddleWidth, left_.rect.y, kPaddleWidth, paddleHeight};
        resetRound(random_() % 2 == 0 ? -1 : 1);
    }
    void startMatch(Mode mode) {
        mode_ = mode;
        scene_ = Scene::Playing;
        paused_ = false;
        resetMatch();
    }

    void updateParticles(float dt) {
        for (auto& p : particles_) {
            if (p.life <= 0.0F) continue;
            p.life -= dt;
            p.position.x += p.velocity.x * dt;
            p.position.y += p.velocity.y * dt;
            p.velocity.x *= std::pow(0.08F, dt);
            p.velocity.y *= std::pow(0.08F, dt);
        }
        flash_ = std::max(0.0F, flash_ - dt * 5.0F);
    }
    void updateTrail(float dt) {
        for (auto& point : trail_) point.age += dt;
        trail_.erase(std::remove_if(trail_.begin(), trail_.end(),
                                   [](const TrailPoint& p) { return p.age > kFireTrailLifetime; }), trail_.end());
    }
    void spawnBurst(Vector2 position, Color color, int count) {
        std::uniform_real_distribution<float> angle(0.0F, 2.0F * PI);
        std::uniform_real_distribution<float> speed(90.0F, 430.0F);
        std::uniform_real_distribution<float> life(0.18F, 0.55F);
        std::uniform_real_distribution<float> radius(2.0F, 6.0F);
        for (int i = 0; i < count; ++i) {
            auto it = std::find_if(particles_.begin(), particles_.end(),
                                   [](const Particle& p) { return p.life <= 0.0F; });
            if (it == particles_.end()) break;
            const float a = angle(random_);
            const float s = speed(random_);
            *it = {position, {std::cos(a) * s, std::sin(a) * s}, color,
                   life(random_), 1.0F, radius(random_)};
            it->maximumLife = it->life;
        }
    }
    void play(const Sound& sound) const { if (audioReady_ && !muted_) PlaySound(sound); }

    void resizeArena(int width, int height) {
        const float scale = std::max(1.0F, static_cast<float>(std::min(width, height))) / 720.0F;
        const float newWidth = std::max(1, width) / scale;
        const float newHeight = std::max(1, height) / scale;
        if (newWidth == worldWidth_ && newHeight == worldHeight_) return;
        const float sx = newWidth / worldWidth_;
        const float sy = newHeight / worldHeight_;
        ball_.position.x *= sx;
        ball_.position.y *= sy;
        for (auto& point : trail_) { point.position.x *= sx; point.position.y *= sy; }
        for (auto& particle : particles_) { particle.position.x *= sx; particle.position.y *= sy; }
        for (Paddle* paddle : {&left_, &right_}) {
            paddle->rect.y *= sy;
            paddle->rect.height = newHeight * (kPaddleHeight / kScreenHeight);
            paddle->rect.y = std::clamp(paddle->rect.y, 0.0F, newHeight - paddle->rect.height);
        }
        left_.rect.x = 32.0F;
        right_.rect.x = newWidth - 32.0F - kPaddleWidth;
        worldWidth_ = arenaRight_ = newWidth;
        worldHeight_ = arenaBottom_ = newHeight;
        ball_.position.y = std::clamp(ball_.position.y, kBallRadius, newHeight - kBallRadius);
        if (ball_.waiting) ball_.position = {newWidth * 0.5F, newHeight * 0.5F};
    }

    bool showMatchHud() const {
        return mode_ != Mode::AiVersusAi || ball_.waiting;
    }

    void triggerShake(float strength, float duration) {
        shake_ = std::max(shake_, strength);
        shakeTime_ = shakeDuration_ = duration;
    }
    void updateImpactEffects(float dt) {
        shakeTime_ = std::max(0.0F, shakeTime_ - dt);
        if (shakeTime_ == 0.0F) shake_ = 0.0F;
        for (Paddle* paddle : {&left_, &right_})
            paddle->recoilTime = std::max(0.0F, paddle->recoilTime - dt);
    }
    Vector2 cameraShake() const {
        const float envelope = shakeDuration_ > 0 ? shakeTime_ / shakeDuration_ : 0;
        const float time = shakeDuration_ - shakeTime_;
        const float amplitude = shake_ * envelope * envelope;
        return {amplitude * (std::cos(time * 105.0F) * 0.7F + std::cos(time * 173.0F) * 0.3F),
                amplitude * (std::sin(time * 137.0F + 0.6F) * 0.55F)};
    }
    float paddleRecoil(const Paddle& paddle) const {
        const float envelope = paddle.recoilTime / 0.32F;
        return paddle.recoilDirection * 5.0F * envelope * envelope *
               std::cos((0.32F - paddle.recoilTime) * 75.0F);
    }

    void draw() {
        const int width = GetScreenWidth();
        const int height = GetScreenHeight();
        const float arenaScale = std::min(width, height) / 720.0F;
        const float uiScale = std::min(width / static_cast<float>(kScreenWidth),
                                       height / static_cast<float>(kScreenHeight));
        const Vector2 shake = cameraShake();
        BeginDrawing();
        ClearBackground(kBackground);
        if (scene_ != Scene::Title) {
            BeginMode2D({{shake.x * arenaScale, shake.y * arenaScale}, {0, 0}, 0, arenaScale});
            drawArena();
            EndMode2D();
        }
        // Menus and overlays fit independently; the arena always fills the window.
        BeginMode2D({{(width - kScreenWidth * uiScale) * 0.5F + shake.x * arenaScale * 0.35F,
                      (height - kScreenHeight * uiScale) * 0.5F + shake.y * arenaScale * 0.35F}, {0, 0}, 0, uiScale});
        if (scene_ == Scene::Title) drawTitle();
        else if (scene_ == Scene::GameOver) drawGameOver();
        else if (paused_) drawPause();
        else if (showMatchHud()) drawMatchHud();
        EndMode2D();
        EndDrawing();
    }
    void drawTitle() const {
        const float glow = 0.72F + std::sin(pulse_ * 2.2F) * 0.18F;
        drawCentered("NEON", 155, 94, FadeColor(teamColors_[0], glow));
        drawCentered("PONG", 250, 150, FadeColor(teamColors_[1], glow));
        drawCentered("A MODERN ARCADE DUEL", 422, 23, kMuted);
        drawButton(465, "1", "SOLO  vs  AI", IsKeyDown(KEY_ONE));
        drawButton(529, "2", "LOCAL  VERSUS", IsKeyDown(KEY_TWO));
        drawButton(593, "3", "AI  vs  AI", IsKeyDown(KEY_THREE));
        drawCentered("ENTER also starts solo", 646, 17, FadeColor(kMuted, 0.75F));
        drawCentered("W/S    PLAYER ONE       UP/DOWN    PLAYER TWO       M    SOUND", 684, 17, kMuted);
    }
    void drawButton(int y, const char* key, const char* label, bool active) const {
        const Rectangle rect{410, static_cast<float>(y), 460, 54};
        DrawRectangleRounded(rect, 0.18F, 8, active ? Color{25, 82, 105, 235} : Color{8, 25, 48, 225});
        DrawRectangleRoundedLines(rect, 0.18F, 8, 2.0F, FadeColor(teamColors_[0], active ? 1.0F : 0.45F));
        DrawText(key, 438, y + 13, 26, kGold);
        DrawText(label, 502, y + 14, 24, kInk);
    }
    void drawArena() const {
        if (mode_ != Mode::AiVersusAi) {
            for (float y = 12; y < worldHeight_; y += 32)
                DrawRectangle(static_cast<int>(worldWidth_ * 0.5F - 2),
                              static_cast<int>(y), 4, 16, Color{107, 155, 178, 100});
        }
        drawPaddle(left_, teamColors_[0]);
        drawPaddle(right_, teamColors_[1]);
        drawFireball();
        for (const auto& p : particles_) {
            if (p.life <= 0.0F) continue;
            const float alpha = p.life / p.maximumLife;
            DrawCircleV(p.position, p.radius * alpha, FadeColor(p.color, alpha));
        }
    }
    void drawMatchHud() const {
        DrawText(TextFormat("%02i", scores_[0]), 485, 20, 64, FadeColor(teamColors_[0], 0.92F));
        DrawText(TextFormat("%02i", scores_[1]), 705, 20, 64, FadeColor(teamColors_[1], 0.92F));
        drawCentered(mode_ == Mode::Solo ? "SOLO MATCH  -  FIRST TO 7" :
                     mode_ == Mode::Versus ? "LOCAL VERSUS  -  FIRST TO 7" :
                     "LEFT vs RIGHT  -  FIRST TO 7", 90, 18, kMuted);
        if (ball_.waiting) {
            const int count = std::max(1, static_cast<int>(std::ceil(serveTimer_)));
            drawCentered(TextFormat("NEXT SERVE IN %i", count), 420, 24, kGold);
        }
        if (mode_ == Mode::AiVersusAi) return;
        if (rally_ >= 4 && !ball_.waiting)
            drawCentered(TextFormat("RALLY  %i", rally_), 650, 18, kGold);
        DrawText("W/S", 35, 674, 18, teamColors_[0]);
        DrawText(mode_ == Mode::Solo ? "AI" : "UP/DOWN", 1120, 674, 18, teamColors_[1]);
        drawCentered("P  PAUSE    R  RESTART    M  SOUND    F11  FULLSCREEN", 681, 16, kMuted);
    }
    void drawFireball() const {
        BeginBlendMode(BLEND_ADDITIVE);
        // Follow the recorded path so fire bends naturally around wall bounces.
        for (std::size_t i = 0; i < trail_.size(); ++i) {
            const auto& point = trail_[i];
            const float heat = Clamp01(1.0F - point.age / kFireTrailLifetime);
            const Vector2 next = i + 1 < trail_.size() ? trail_[i + 1].position : ball_.position;
            const float dx = next.x - point.position.x;
            const float dy = next.y - point.position.y;
            const float length = std::max(0.001F, std::hypot(dx, dy));
            const Vector2 normal{-dy / length, dx / length};
            const float flicker = std::sin(pulse_ * 28.0F - point.age * 65.0F);
            const float spread = (1.0F - heat) * 12.0F;
            const Vector2 flame{point.position.x + normal.x * flicker * spread,
                                point.position.y + normal.y * flicker * spread};
            const float radius = (3.0F + 12.0F * heat) * (0.9F + flicker * 0.1F);
            DrawCircleV(flame, radius * 1.9F, FadeColor(kFireRed, heat * 0.08F));
            DrawLineEx(flame, next, radius * 1.7F, FadeColor(kFireRed, heat * 0.32F));
            DrawCircleV(flame, radius, FadeColor(kFireOrange, heat * 0.5F));
            DrawLineEx(flame, next, radius * 0.65F, FadeColor(kFireYellow, heat * heat * 0.65F));
            if (i % 4 == 0) {
                const float side = i % 8 == 0 ? 1.0F : -1.0F;
                const float drift = (1.0F - heat) * 32.0F;
                const Vector2 ember{flame.x + normal.x * side * drift,
                                    flame.y + normal.y * side * drift - point.age * 24.0F};
                DrawCircleV(ember, 1.0F + heat * 1.4F, FadeColor(kFireOrange, heat * 0.8F));
            }
        }
        const float flicker = 1.0F + std::sin(pulse_ * 31.0F) * 0.08F;
        DrawCircleGradient(static_cast<int>(ball_.position.x), static_cast<int>(ball_.position.y),
                           kBallRadius * 3.8F * flicker, FadeColor(kFireOrange, 0.35F + flash_ * 0.15F), BLANK);
        for (int i = 0; i < 9; ++i) {
            const float angle = i * (2.0F * PI / 9.0F) + pulse_ * 2.0F;
            const float reach = kBallRadius * (0.9F + 0.24F * std::sin(pulse_ * 23.0F + i * 2.1F));
            const Vector2 flame{ball_.position.x + std::cos(angle) * reach,
                                ball_.position.y + std::sin(angle) * reach};
            DrawCircleV(flame, 5.0F * flicker, FadeColor(kFireOrange, 0.75F));
        }
        EndBlendMode();
        // Keep a crisp, readable core at the actual collision radius.
        DrawCircleV(ball_.position, kBallRadius, kFireOrange);
        DrawCircleV(ball_.position, kBallRadius * 0.8F, kFireYellow);
        DrawCircleV(ball_.position, kBallRadius * 0.53F, Color{255, 251, 221, 255});
    }

    void drawPaddle(const Paddle& paddle, Color color) const {
        Rectangle visual = paddle.rect;
        visual.x += paddleRecoil(paddle);
        const Rectangle glow{visual.x - 9, visual.y - 9,
                             visual.width + 18, visual.height + 18};
        DrawRectangleRounded(glow, 0.45F, 10, FadeColor(color, 0.12F));
        DrawRectangleRounded(visual, 0.65F, 10, color);
        DrawRectangleRounded({visual.x + 4, visual.y + 4,
                              visual.width - 8, visual.height - 8},
                             0.65F, 10, FadeColor(WHITE, 0.24F));
    }
    void drawPause() const {
        DrawRectangle(0, 0, kScreenWidth, kScreenHeight, Color{1, 4, 12, 190});
        drawCentered("PAUSED", 271, 74, kInk);
        drawCentered("P or ESC to continue", 371, 24, kMuted);
        drawCentered("R to restart the match", 410, 19, kMuted);
    }
    void drawGameOver() const {
        DrawRectangle(0, 0, kScreenWidth, kScreenHeight, Color{1, 4, 12, 205});
        const Color color = winner_ == 0 ? teamColors_[0] : teamColors_[1];
        drawCentered(mode_ == Mode::AiVersusAi ? (winner_ == 0 ? "LEFT TEAM WINS" : "RIGHT TEAM WINS") : winner_ == 0 ? "PLAYER ONE WINS" :
                     mode_ == Mode::Solo ? "THE AI WINS" : "PLAYER TWO WINS", 248, 64, color);
        drawCentered(TextFormat("%02i  -  %02i", scores_[0], scores_[1]), 332, 48, kInk);
        if (mode_ == Mode::AiVersusAi) {
            drawCentered("NEXT MATCH IN 3 SECONDS", 431, 25, kGold);
            return;
        }
        drawCentered("ENTER  REMATCH", 431, 25, kGold);
        drawCentered("ESC  MAIN MENU", 474, 18, kMuted);
    }
    void drawCentered(const char* text, int y, int size, Color color) const {
        DrawText(text, (kScreenWidth - MeasureText(text, size)) / 2, y, size, color);
    }

    float worldWidth_{1280.0F};
    float worldHeight_{720.0F};
    float arenaLeft_{};
    float arenaRight_{1280.0F};
    float arenaTop_{};
    float arenaBottom_{720.0F};
    Scene scene_{Scene::Title};
    Mode mode_{Mode::Solo};
    Paddle left_{};
    Paddle right_{};
    Ball ball_{};
    std::array<int, 2> scores_{};
    std::array<Particle, kParticleCount> particles_{};
    std::vector<TrailPoint> trail_{};
    std::array<Color, 2> teamColors_{kBlue, kPink};
    std::mt19937 random_;
    int serveDirection_{1};
    int rally_{};
    int winner_{};
    float serveTimer_{1.25F};
    float trailTimer_{};
    float pulse_{};
    float shake_{};
    float shakeTime_{};
    float shakeDuration_{};
    float flash_{};
    bool screensaver_{};
    bool preview_{};
    float duration_{};
    float elapsed_{};
    float rematchTimer_{};
    float speedIncreaseTimer_{};
    float speedBonus_{};
    bool paused_{};
    bool muted_{};
    bool audioReady_{};
    Sound paddleSound_{};
    Sound wallSound_{};
    Sound scoreSound_{};
};
}  // namespace

int main(int argc, char** argv) {
    bool saver = false, preview = false, ai = false;
    int monitor = 0, width = kScreenWidth, height = kScreenHeight;
    std::string lockOutput;
    float duration = 0, teamHue = -1;
    try {
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            auto value = [&]() { if (++i >= argc) throw std::runtime_error("Missing value for " + arg); return std::string(argv[i]); };
            if (arg == "--lock-frames") { lockOutput = value(); saver = preview = true; }
            else if (arg == "--width") width = std::stoi(value());
            else if (arg == "--height") height = std::stoi(value());
            else if (arg == "--screensaver") saver = true;
            else if (arg == "--preview") saver = preview = true;
            else if (arg == "--ai-vs-ai") ai = true;
            else if (arg == "--monitor") monitor = std::stoi(value());
            else if (arg == "--team-hue") { teamHue = std::stof(value()); if (!std::isfinite(teamHue) || teamHue < 0 || teamHue >= 360) throw std::runtime_error("Team hue must be in [0, 360)"); }
            else if (arg == "--duration") duration = std::stof(value());
            else if (arg == "--help" || arg == "-h") {
                std::cout << "pong [--ai-vs-ai] [--screensaver | --preview] [--monitor n] [--team-hue degrees] [--duration seconds] [--lock-frames path --width px --height px]\n";
                return 0;
            } else throw std::runtime_error("Unknown option: " + arg);
        }
        if (monitor < 0 || duration < 0 || !std::isfinite(duration) || width < 100 || height < 100 || width > 16384 || height > 16384) throw std::runtime_error("Invalid monitor or duration");
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
    if (!lockOutput.empty()) {
        SetTraceLogLevel(LOG_WARNING);
        const float scale = std::min(1.0F, 1280.0F / std::max(width, height));
        width = std::max(1, static_cast<int>(width * scale));
        height = std::max(1, static_cast<int>(height * scale));
    }
    try {
        PongGame game(saver, preview, ai, monitor, duration, !lockOutput.empty(), width, height, teamHue);
        if (!lockOutput.empty()) game.runLockFrames(lockOutput);
        else game.run();
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
    return EXIT_SUCCESS;
}
