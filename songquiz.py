import random
import os
import tkinter as tk
from tkinter import messagebox
import pygame
import time
import threading
from mutagen.mp3 import MP3
import subprocess
import json
import tempfile

class SongQuizGenerator:
    def __init__(self, playlist_url, num_choices=5, excerpt_length=30):
        self.playlist_url = playlist_url
        self.num_choices = num_choices
        self.excerpt_length = excerpt_length
        self.songs = []
        self.current_song = None
        self.current_choices = []
        self.temp_dir = tempfile.mkdtemp()
        self.current_audio_file = None
        pygame.mixer.init()
    
    def fetch_playlist(self):
        """Fetch playlist info using yt-dlp"""
        try:
            print(f"Fetching playlist: {self.playlist_url}")
            
            # Get playlist info using yt-dlp
            command = [
                "yt-dlp", 
                "--flat-playlist", 
                "--dump-json",
                self.playlist_url
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                print("Error running yt-dlp:", result.stderr)
                return False
            
            # Parse the output line by line (each line is a JSON object)
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    item = json.loads(line)
                    self.songs.append({
                        'title': item.get('title', 'Unknown Title'),
                        'id': item.get('id', ''),
                        'url': f"https://www.youtube.com/watch?v={item.get('id', '')}",
                        'duration': item.get('duration', 0)
                    })
                    print(f"Added: {item.get('title', 'Unknown Title')}")
                except json.JSONDecodeError:
                    print(f"Error parsing JSON: {line}")
            
            print(f"Successfully loaded {len(self.songs)} songs from playlist.")
            return len(self.songs) > 0
        except Exception as e:
            print(f"Error fetching playlist: {str(e)}")
            return False
    
    def download_audio(self, song):
        """Download audio for a specific song"""
        try:
            print(f"Downloading: {song['title']}")
            
            # Create a filename based on the video ID
            filename = os.path.join(self.temp_dir, f"{song['id']}.mp3")
            
            # Check if already downloaded
            if os.path.exists(filename):
                print(f"Using cached file for {song['title']}")
                return filename
            
            # Download the audio using yt-dlp
            command = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--audio-quality", "128K",
                "-o", filename,
                song['url']
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error downloading {song['title']}: {result.stderr}")
                return None
            
            return filename
        except Exception as e:
            print(f"Error downloading audio: {str(e)}")
            return None
    
    def generate_quiz_question(self):
        """Generate a random song excerpt and multiple choice options"""
        if len(self.songs) < self.num_choices:
            print("Not enough songs in playlist!")
            return False
        
        # Clear any previous audio file
        self.stop_playback()
        
        # Select random song for the excerpt
        self.current_song = random.choice(self.songs)
        
        # Download the audio
        self.current_audio_file = self.download_audio(self.current_song)
        if not self.current_audio_file:
            print(f"Failed to download audio for {self.current_song['title']}")
            return False
        
        # Generate other choices for multiple choice
        all_songs_except_current = [song for song in self.songs if song != self.current_song]
        other_choices = random.sample(all_songs_except_current, min(self.num_choices-1, len(all_songs_except_current)))
        
        # Create the final choices list with correct answer at random position
        self.current_choices = other_choices.copy()
        correct_position = random.randint(0, len(self.current_choices))
        self.current_choices.insert(correct_position, self.current_song)
        
        return True
    
    def play_excerpt(self):
        """Play a random 30-second excerpt of the current song"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            print("No audio loaded!")
            return False
        
        try:
            # Get song duration
            audio = MP3(self.current_audio_file)
            duration = audio.info.length
            
            # Choose random starting point (making sure we have enough time for the excerpt)
            max_start_time = max(0, duration - self.excerpt_length)
            if max_start_time <= 0:
                start_time = 0
            else:
                start_time = random.uniform(0, max_start_time)
            
            # Load and play the song starting from the chosen point
            pygame.mixer.music.load(self.current_audio_file)
            pygame.mixer.music.play(start=start_time)
            
            # Set a timer to stop playback after excerpt_length seconds
            threading.Timer(self.excerpt_length, self.stop_playback).start()
            
            return True
        except Exception as e:
            print(f"Error playing excerpt: {str(e)}")
            return False
    
    def stop_playback(self):
        """Stop the current playback"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    
    def cleanup(self):
        """Clean up temporary files"""
        self.stop_playback()
        pygame.mixer.quit()
        
        # Remove temporary files
        for file in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, file))
            except:
                pass
        try:
            os.rmdir(self.temp_dir)
        except:
            pass

# GUI Application
class SongQuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Music Quiz Generator")
        self.root.geometry("600x500")
        self.quiz = None
        
        # Create widgets
        self.create_widgets()
    
    def create_widgets(self):
        # Playlist URL input
        tk.Label(self.root, text="YouTube Music Playlist URL:").pack(pady=(20, 5))
        self.playlist_url_entry = tk.Entry(self.root, width=50)
        self.playlist_url_entry.pack(pady=(0, 20))
        
        # Load playlist button
        self.load_button = tk.Button(self.root, text="Load Playlist", command=self.load_playlist)
        self.load_button.pack(pady=(0, 20))
        
        # Status label
        self.status_label = tk.Label(self.root, text="Enter a YouTube Music playlist URL to begin")
        self.status_label.pack(pady=(0, 20))
        
        # Quiz frame (initially hidden)
        self.quiz_frame = tk.Frame(self.root)
        
        # Play button
        self.play_button = tk.Button(self.quiz_frame, text="Play Random Excerpt", command=self.play_excerpt)
        self.play_button.pack(pady=(0, 20))
        
        # Multiple choice options
        self.choice_frame = tk.Frame(self.quiz_frame)
        self.choice_frame.pack(fill="both", expand=True)
        
        self.choice_var = tk.IntVar()
        self.choice_var.set(-1)  # No selection by default
        self.choice_radios = []
        
        for i in range(5):  # Default to 5 choices
            radio = tk.Radiobutton(self.choice_frame, text=f"Option {i+1}", variable=self.choice_var, value=i)
            radio.pack(anchor="w", pady=5)
            self.choice_radios.append(radio)
        
        # Submit button
        self.submit_button = tk.Button(self.quiz_frame, text="Submit Answer", command=self.check_answer)
        self.submit_button.pack(pady=20)
        
        # Next question button
        self.next_button = tk.Button(self.quiz_frame, text="Next Question", command=self.next_question)
        self.next_button.pack(pady=(0, 20))
    
    def load_playlist(self):
        url = self.playlist_url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid YouTube or YouTube Music playlist URL")
            return
        
        self.status_label.config(text="Loading playlist... This may take a moment.")
        self.root.update()
        
        self.quiz = SongQuizGenerator(url)
        success = self.quiz.fetch_playlist()
        
        if success and len(self.quiz.songs) >= 5:
            self.status_label.config(text=f"Loaded {len(self.quiz.songs)} songs. Ready to play!")
            self.quiz_frame.pack(fill="both", expand=True)
            self.next_question()
        elif success and len(self.quiz.songs) > 0:
            messagebox.showwarning("Warning", f"Found only {len(self.quiz.songs)} songs. Continuing with fewer options.")
            self.quiz.num_choices = min(5, len(self.quiz.songs))
            self.status_label.config(text=f"Loaded {len(self.quiz.songs)} songs. Ready to play!")
            self.quiz_frame.pack(fill="both", expand=True)
            self.next_question()
        else:
            messagebox.showerror("Error", "Failed to load playlist or no songs found")
            self.status_label.config(text="Please enter a valid YouTube playlist URL")
    
    def play_excerpt(self):
        if self.quiz:
            self.quiz.play_excerpt()
    
    def update_choices(self):
        # Update the radio buttons with song titles
        for i, radio in enumerate(self.choice_radios):
            if i < len(self.quiz.current_choices):
                radio.config(text=self.quiz.current_choices[i]['title'], value=i)
                radio.pack(anchor="w", pady=5)
            else:
                radio.pack_forget()  # Hide extra radio buttons
        
        self.choice_var.set(-1)  # Reset selection
    
    def next_question(self):
        if not self.quiz:
            return
        
        self.status_label.config(text="Generating new question... downloading song...")
        self.root.update()
        
        success = self.quiz.generate_quiz_question()
        if success:
            self.update_choices()
            self.status_label.config(text="New question ready. Click 'Play Random Excerpt' to hear the song.")
            self.quiz.play_excerpt()
        else:
            messagebox.showerror("Error", "Failed to generate a new question. Try again.")
            self.next_question()  # Try another song
    
    def check_answer(self):
        selected = self.choice_var.get()
        
        if selected == -1:
            messagebox.showinfo("Info", "Please select an answer first")
            return
        
        correct_song = self.quiz.current_song
        selected_song = self.quiz.current_choices[selected]
        
        if selected_song == correct_song:
            messagebox.showinfo("Correct!", "You got it right! The song is: " + correct_song['title'])
        else:
            messagebox.showinfo("Incorrect", f"Sorry, that's wrong. The correct song is: {correct_song['title']}")

def main():
    root = tk.Tk()
    app = SongQuizApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(app))
    root.mainloop()

def on_close(app):
    if app.quiz:
        app.quiz.cleanup()
    app.root.destroy()

if __name__ == "__main__":
    main()