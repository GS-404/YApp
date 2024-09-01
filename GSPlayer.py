from yandex_music import Client
import vlc
import requests
import customtkinter as ctk
from PIL import Image, ImageTk
from io import BytesIO
import threading

TOKEN = 'YOUR TOKEN'

class MusicPlayer:
    def __init__(self, token, root):
        self.client = Client(token).init()
        self.track_index = 0
        self.player = None
        self.liked_tracks = self.client.users_likes_tracks()
        self.my_wave_tracks = [] 
        self.track_count = len(self.liked_tracks.tracks)
        self.is_paused = False
        self.is_my_wave_active = False  
        self.root = root
        self.update_seek = False  
        self.seeking = False  
        self.current_track = None  

        self.init_ui()

    def init_ui(self):
        self.root.title("GS Player v1.0 @Hash403")
        self.root.geometry("470x670")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.track_frame = ctk.CTkFrame(self.root)
        self.track_frame.pack(pady=10)

        self.album_art_label = ctk.CTkLabel(self.track_frame, text="")
        self.album_art_label.pack()

        self.track_info_label = ctk.CTkLabel(self.track_frame, text="Track Info", font=("Helvetica", 12))
        self.track_info_label.pack()

        self.controls_frame = ctk.CTkFrame(self.root)
        self.controls_frame.pack(pady=10)

        self.prev_button = ctk.CTkButton(self.controls_frame, text="◄◄", width=5, command=self.on_prev)
        self.prev_button.grid(row=0, column=0, padx=5)

        self.play_button = ctk.CTkButton(self.controls_frame, text="▶", width=5, command=self.on_play)
        self.play_button.grid(row=0, column=1, padx=5)

        self.pause_button = ctk.CTkButton(self.controls_frame, text="⏸", width=5, command=self.on_pause)
        self.pause_button.grid(row=0, column=2, padx=5)

        self.stop_button = ctk.CTkButton(self.controls_frame, text="■", width=5, command=self.on_stop)
        self.stop_button.grid(row=0, column=3, padx=5)

        self.next_button = ctk.CTkButton(self.controls_frame, text="►►", width=5, command=self.on_next)
        self.next_button.grid(row=0, column=4, padx=5)

        self.favorite_button = ctk.CTkButton(self.controls_frame, text="♡", width=5, command=self.toggle_current_favorite)
        self.favorite_button.grid(row=0, column=5, padx=5)

        self.download_button = ctk.CTkButton(self.root, text="Скачать", command=self.on_download)
        self.download_button.pack(pady=10)

        self.my_wave_button = ctk.CTkButton(self.root, text="Моя волна", command=self.on_my_wave)
        self.my_wave_button.pack(pady=10)

        self.volume_scale = ctk.CTkSlider(self.root, from_=0, to=100, command=self.on_volume_change)
        self.volume_scale.set(50)
        self.volume_scale.pack(pady=10)

        self.time_frame = ctk.CTkFrame(self.root)
        self.time_frame.pack(pady=5)

        self.current_time_label = ctk.CTkLabel(self.time_frame, text="0:00")
        self.current_time_label.grid(row=0, column=0, padx=5)

        self.seek_scale = ctk.CTkSlider(self.time_frame, from_=0, to=100, command=self.on_seek_change)
        self.seek_scale.grid(row=0, column=1, padx=5)
        self.seek_scale.bind("<Button-1>", self.on_seek_press)
        self.seek_scale.bind("<ButtonRelease-1>", self.on_seek_release)

        self.total_time_label = ctk.CTkLabel(self.time_frame, text="0:00")
        self.total_time_label.grid(row=0, column=2, padx=5)

        self.tracks_frame = ctk.CTkScrollableFrame(self.root, width=550, height=300)
        self.tracks_frame.pack(pady=10, fill="both", expand=True)

        self.update_tracks_list()

        self.update_seek_bar()

    def update_tracks_list(self):
        for widget in self.tracks_frame.winfo_children():
            widget.destroy()

        for idx, item in enumerate(self.liked_tracks.tracks):
            try:
                track = item.fetch_track()
                if not track:
                    print(f"Трек с индексом {idx} отсутствует или имеет неполную информацию.")
                    continue

                cover_uri = f"https://{track.cover_uri.replace('%%', '50x50')}"
                image_data = requests.get(cover_uri).content
                image = Image.open(BytesIO(image_data))
                cover_image = ctk.CTkImage(image, size=(50, 50))

                cover_label = ctk.CTkLabel(self.tracks_frame, image=cover_image, text="")
                cover_label.image = cover_image
                cover_label.grid(row=idx, column=0, padx=5, pady=5)

                play_button = ctk.CTkButton(
                    self.tracks_frame,
                    text="▶",
                    width=5,
                    command=lambda idx=idx: self.play_track_by_index(idx)
                )
                play_button.grid(row=idx, column=1, padx=5)

                track_label = ctk.CTkLabel(
                    self.tracks_frame,
                    text=f"{track.title}\n{', '.join(artist.name for artist in track.artists)}"
                )
                track_label.grid(row=idx, column=2, padx=5)

                is_favorite = self.is_track_favorite(item.id)

                favorite_button = ctk.CTkButton(
                    self.tracks_frame,
                    text="♡" if not is_favorite else "♥",
                    width=5,
                    command=lambda idx=idx: self.toggle_favorite(idx)
                )
                favorite_button.grid(row=idx, column=3, padx=5)

                duration_label = ctk.CTkLabel(
                    self.tracks_frame,
                    text=self.format_duration(track.duration_ms)
                )
                duration_label.grid(row=idx, column=4, padx=5)
            except Exception as e:
                print(f"Ошибка при загрузке трека с индексом {idx}: {e}")

    def is_track_favorite(self, track_id):
        return any(track.id == track_id for track in self.liked_tracks.tracks)

    def toggle_favorite(self, index):
        try:
            track_id = self.liked_tracks.tracks[index].id
            if self.is_track_favorite(track_id):
                self.client.users_dislikes_tracks_remove(track_id)
                print(f"Трек с ID {track_id} удален из избранного.")
            else:
                self.client.users_likes_tracks_add(track_id)
                print(f"Трек с ID {track_id} добавлен в избранное.")

            self.liked_tracks = self.client.users_likes_tracks()
            self.update_tracks_list()  
        except Exception as e:
            print(f"Ошибка при попытке изменить статус избранного: {e}")

    def toggle_current_favorite(self):
        try:
            if self.current_track:
                track_id = self.current_track.track_id
                if self.is_track_favorite(track_id):
                    self.client.users_dislikes_tracks_remove(track_id)
                    print(f"Трек с ID {track_id} удален из избранного.")
                    self.favorite_button.configure(text="♡")
                else:
                    self.client.users_likes_tracks_add(track_id)
                    print(f"Трек с ID {track_id} добавлен в избранное.")
                    self.favorite_button.configure(text="♥")

                self.liked_tracks = self.client.users_likes_tracks()  
                self.update_tracks_list() 
            else:
                print("Нет текущего трека для добавления в избранное.")
        except Exception as e:
            print(f"Ошибка при попытке изменить статус избранного: {e}")

    def play_track_by_index(self, index):
        self.track_index = index
        self.play_track()

    def update_track_info(self, track):
        self.track_info_label.configure(text=f"{track.title} - {', '.join(artist.name for artist in track.artists)}")

        cover_uri = f"https://{track.cover_uri.replace('%%', '200x200')}"
        image_data = requests.get(cover_uri).content
        image = Image.open(BytesIO(image_data))
        cover_image = ctk.CTkImage(image, size=(200, 200))
        self.album_art_label.configure(image=cover_image)
        self.album_art_label.image = cover_image

        self.total_time_label.configure(text=self.format_duration(track.duration_ms))

        if self.is_track_favorite(track.id):
            self.favorite_button.configure(text="♥")
        else:
            self.favorite_button.configure(text="♡")

    def play_track(self, track=None):
        if track is None:
            track = self.liked_tracks.tracks[self.track_index].fetch_track()

        if track:
            self.current_track = track
            self.update_track_info(track)
            download_info_list = track.get_download_info()

            if download_info_list:
                best_quality = download_info_list[0]
                download_url = best_quality.get_direct_link()

                if download_url:
                    print(f"Воспроизведение: {track.title} - {', '.join(artist.name for artist in track.artists)}")
                    audio_data = requests.get(download_url).content
                    with open("temp_audio.mp3", "wb") as f:
                        f.write(audio_data)

                    if self.player:
                        self.player.stop()

                    self.player = vlc.MediaPlayer("temp_audio.mp3")
                    self.player.play()
                    self.update_seek = True 
                else:
                    print("Не удалось получить прямую ссылку для загрузки.")
            else:
                print("Не удалось получить информацию о загрузке трека.")
        else:
            print(f"Не удалось загрузить трек с индексом {self.track_index}.")

    def stop(self):
        if self.player:
            self.player.stop()
        self.update_seek = False 

    def pause(self):
        if self.player:
            self.player.pause()
            self.is_paused = not self.is_paused

    def resume(self):
        if self.player:
            self.player.play()

    def set_volume(self, volume):
        if self.player:
            self.player.audio_set_volume(int(volume))

    def next_track(self):
        self.stop()
        if self.is_my_wave_active:
            self.track_index = (self.track_index + 1) % len(self.my_wave_tracks)
            self.play_next_my_wave()
        else:
            self.track_index = (self.track_index + 1) % self.track_count
            self.play_track()

    def prev_track(self):
        self.stop()
        if self.is_my_wave_active:
            self.track_index = (self.track_index - 1) % len(self.my_wave_tracks)
            self.play_next_my_wave()
        else:
            self.track_index = (self.track_index - 1) % self.track_count
            self.play_track()

    def download_track(self):
        track = self.liked_tracks.tracks[self.track_index].fetch_track()
        if track:
            download_info_list = track.get_download_info()

            if download_info_list:
                best_quality = download_info_list[0]
                download_url = best_quality.get_direct_link()

                if download_url:
                    print(f"Скачивание: {track.title} - {', '.join(artist.name for artist in track.artists)}")
                    audio_data = requests.get(download_url).content

                    file_name = f"{track.title} - {', '.join(artist.name for artist in track.artists)}.mp3"

                    with open(file_name, "wb") as f:
                        f.write(audio_data)
                    print(f"Трек сохранен как {file_name}")
                else:
                    print("Не удалось получить прямую ссылку для загрузки.")
            else:
                print("Не удалось получить информацию о загрузке трека.")
        else:
            print(f"Не удалось загрузить трек с индексом {self.track_index} для загрузки.")

    def play_my_wave(self):
        station_tracks_result = self.client.rotor_station_tracks("user:onyourwave")
        self.my_wave_tracks = station_tracks_result.sequence
        self.track_index = 0
        self.is_my_wave_active = True 

        if self.my_wave_tracks:
            self.play_next_my_wave()

    def play_next_my_wave(self):
        if self.my_wave_tracks and self.track_index < len(self.my_wave_tracks):
            track_id = self.my_wave_tracks[self.track_index].track.track_id
            track = self.client.tracks([track_id])[0]
            self.play_track(track)
            self.track_index += 1
        else:
            print("Нет доступных треков в 'Моя волна' или воспроизведение завершено.")

    def on_seek_change(self, val):
        if self.player and self.seeking:
            new_time = int(float(val) * self.player.get_length() / 100)
            self.player.set_time(new_time)

    def on_seek_press(self, event):
        self.seeking = True
        self.update_seek = False 

    def on_seek_release(self, event):
        self.seeking = False
        self.update_seek = True 

    def update_seek_bar(self):
        if self.player and self.update_seek and not self.seeking:
            length = self.player.get_length()  
            current_time = self.player.get_time() 
            if length > 0:
                self.seek_scale.set((current_time / length) * 100) 
                self.current_time_label.configure(text=self.format_duration(current_time))

        self.root.after(1000, self.update_seek_bar)

    def format_duration(self, duration_ms):
        seconds = (duration_ms // 1000) % 60
        minutes = (duration_ms // (1000 * 60)) % 60
        return f"{minutes}:{seconds:02}"

    def on_play(self):
        if not self.is_paused:
            player_thread = threading.Thread(target=self.play_track)
            player_thread.start()
        else:
            self.resume()
            self.is_paused = False

    def on_stop(self):
        self.stop()

    def on_pause(self):
        self.pause()

    def on_next(self):
        player_thread = threading.Thread(target=self.next_track)
        player_thread.start()

    def on_prev(self):
        player_thread = threading.Thread(target=self.prev_track)
        player_thread.start()

    def on_volume_change(self, val):
        volume = int(float(val))
        self.set_volume(volume)

    def on_download(self):
        download_thread = threading.Thread(target=self.download_track)
        download_thread.start()

    def on_my_wave(self):
        wave_thread = threading.Thread(target=self.play_my_wave)
        wave_thread.start()


if __name__ == "__main__":
    root = ctk.CTk()
    player = MusicPlayer(TOKEN, root)
    root.mainloop()