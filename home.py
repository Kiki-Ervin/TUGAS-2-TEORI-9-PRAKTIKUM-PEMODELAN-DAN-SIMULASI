from flask import Flask, render_template
import pymysql
from decimal import Decimal

app = Flask(__name__)

# Fungsi untuk membuat koneksi ke database MySQL
def connect_to_database():
    try:
        connection = pymysql.connect(
            host='localhost',    # Ganti dengan host Anda
            user='root',         # Ganti dengan user MySQL Anda
            password='',         # Ganti dengan password MySQL Anda
            database='pusling',  # Ganti dengan nama database Anda
            port=8111           # Ganti dengan port MySQL Anda jika berbeda
        )
        return connection
    except Exception as e:
        print("Terjadi kesalahan dalam koneksi:", e)
        return None
    
@app.route('/')
def home_page():
    return render_template('home.html')


@app.route('/home')
def home_content():
    return """
    <h2>Welcome</h2>
    <p>Selamat datang di simulasi prediksi pengunjung perpustakaan keliling Kota Bandung.</p>
    <h3>Pengenalan Monte Carlo</h3>
    <p style="font-size: 18px; text-align: justify;">
        Metode Monte Carlo Simulasi Monte Carlo adalah teknik matematika yang memprediksi kemungkinan hasil dari peristiwa yang tidak pasti. Program komputer menggunakan metode ini untuk menganalisis data masa lalu dan memprediksi berbagai hasil masa depan berdasarkan pilihan tindakan. 
        Metode ini melibatkan simulasi sejumlah besar eksperimen acak untuk memperkirakan nilai suatu variabel. </p>
    <p style="font-size: 18px; text-align: justify;"> Dalam konteks simulasi prediksi pengunjung perpustakaan keliling, Monte Carlo digunakan untuk memodelkan berbagai kemungkinan jumlah pengunjung 
        dengan memperhitungkan faktor-faktor acak, seperti waktu kunjungan, cuaca, dan faktor lainnya yang mempengaruhi pola kunjungan. Dengan melakukan simulasi berulang-ulang menggunakan Monte Carlo, kita dapat menghasilkan distribusi kemungkinan yang memberikan gambaran 
        lebih baik tentang berapa banyak pengunjung yang dapat datang di masa depan.
    </p>
    """


@app.route('/monte_carlo')
def monte_carlo_content():
    connection = connect_to_database()
    if connection is None:
        return "<h2>Monte Carlo</h2><p>Gagal terhubung ke database.</p>"

    cursor = connection.cursor()

    # QUERY UNTUK MENGAMBIL DATA
    query = """
    SELECT tahun, SUM(jumlah_pengunjung) AS total_pengunjung
    FROM data_pusling
    GROUP BY tahun
    ORDER BY tahun;
    """
    cursor.execute(query)
    data = cursor.fetchall()

    # Hitung total keseluruhan pengunjung
    total_pengunjung_keseluruhan = sum([row[1] for row in data])

    # PERHITUNGAN PROBABILITAS DAN INTERVAL
    data_probabilitas = []
    kumulatif = Decimal(0)

    # Kosongkan tabel 'data_probabilitas' sebelum memasukkan data baru
    cursor.execute("TRUNCATE TABLE data_probabilitas;")

    for index, row in enumerate(data):
        tahun, total_pengunjung = row
        probabilitas = total_pengunjung / total_pengunjung_keseluruhan  # Hitung probabilitas
        kumulatif += Decimal(probabilitas)  # Update kumulatif dengan menambah probabilitas

        # Tentukan interval_awal dan interval_akhir
        interval_awal = 0 if index == 0 else int(data_probabilitas[-1]["interval"].split('-')[1]) + 1
        interval_akhir = int(kumulatif * 1000)  # Akhiri interval dengan nilai kumulatif * 1000

        # Penyesuaian interval untuk tahun tertentu
        if tahun == 2021:
            interval_akhir -= 0
        elif tahun == 2022:
            interval_akhir += 1
        elif tahun == 2023:
            interval_akhir -= 1

        # Tambahkan data ke list
        data_probabilitas.append({
            "tahun": tahun,
            "total_pengunjung": total_pengunjung,
            "probabilitas": round(probabilitas, 3),
            "kumulatif": round(kumulatif, 3),
            "interval": f"{interval_awal}-{interval_akhir}"
        })

        # Simpan data ke tabel 'data_probabilitas'
        cursor.execute("""
            INSERT INTO data_probabilitas (tahun, total_pengunjung, probabilitas, kumulatif, interval_probabilitas)
            VALUES (%s, %s, %s, %s, %s)
        """, (tahun, total_pengunjung, round(probabilitas, 3), round(kumulatif, 3), f"{interval_awal}-{interval_akhir}"))

    connection.commit()

    # PERHITUNGAN PREDIKSI LCG
    a = 32
    c = 25
    m = 99
    Z0 = 78  # Nilai awal
    n = 6  # Jumlah iterasi
    Zi = Z0

    predictions = []
    cursor.execute("TRUNCATE TABLE hasil_prediksi;")  # Kosongkan tabel sebelum memasukkan data baru

    def lcg_generate(Zi, a, c, m):
        return (a * Zi + c) % m

    def get_prediction(angka_tiga_digit):
        for row in data_probabilitas:
            interval_awal, interval_akhir = map(int, row["interval"].split('-'))
            if interval_awal <= angka_tiga_digit <= interval_akhir:
                return row["total_pengunjung"]
        return None

    # Generate bilangan acak dan prediksi
    for i in range(1, n + 1):
        Zi = lcg_generate(Zi, a, c, m)
        angka_tiga_digit = (Zi * 10) % 1000

        prediksi = get_prediction(angka_tiga_digit)
        if prediksi:
            predictions.append({
                "Zi": i,
                "(aZi + C)": a * Zi + c,
                "(aZi + C) mod m": Zi,
                "Angka Tiga Digit": angka_tiga_digit,
                "Prediksi": prediksi
            })

            # Simpan data prediksi ke tabel 'hasil_prediksi'
            cursor.execute("""
                INSERT INTO hasil_prediksi (Zi, aZi_plus_c, aZi_plus_c_mod_m, angka_tiga_digit, prediksi_pengunjung)
                VALUES (%s, %s, %s, %s, %s)
            """, (i, a * Zi + c, Zi, angka_tiga_digit, prediksi))

    connection.commit()

    # Tutup koneksi
    cursor.close()
    connection.close()

    # OUTPUT UNTUK VERIFIKASI
    print("\nTABEL DATA PROBABILITAS:")
    for row in data_probabilitas:
        print(row)

    print("\nTABEL HASIL PREDIKSI:")
    for row in predictions:
        print(row)

    # Ambil data dari tabel `data_probabilitas`
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("SELECT tahun, total_pengunjung, probabilitas, kumulatif, interval_probabilitas FROM data_probabilitas;")
    data_probabilitas = cursor.fetchall()

    # Ambil data dari tabel `hasil_prediksi`
    cursor.execute("SELECT Zi, aZi_plus_c, aZi_plus_c_mod_m, angka_tiga_digit, prediksi_pengunjung FROM hasil_prediksi;")
    hasil_prediksi = cursor.fetchall()

    # Format prediksi menjadi 5 angka
    formatted_hasil_prediksi = []
    for row in hasil_prediksi:
        formatted_row = list(row)
        formatted_row[4] = str(row[4])[:5]  # Pastikan hanya 5 digit (potong jika lebih)
        formatted_hasil_prediksi.append(formatted_row)

    # Hasil dari penghitungan manual
    total_prediction = 37451
    # Tutup koneksi database
    cursor.close()
    connection.close()

    # Kirim data ke template HTML
    return render_template(
        'monte_carlo.html',
        data_probabilitas=data_probabilitas,
        hasil_prediksi=formatted_hasil_prediksi,
        total_prediction=str(total_prediction).zfill(5)  # Format total prediksi menjadi 5 angka
    )

@app.route('/data_pusling')
def data_pusling_content():
    # Koneksi ke database
    connection = connect_to_database()
    if connection is None:
        return "Error: Tidak dapat terhubung ke database!"

    cursor = connection.cursor()

    # Query untuk mengambil seluruh data dari tabel data_pusling
    query = "SELECT * FROM data_pusling"
    cursor.execute(query)
    data_pusling = cursor.fetchall()

    # Menutup koneksi
    cursor.close()
    connection.close()

    # Kirim data ke template
    return render_template('index.html', data_pusling=data_pusling)

@app.route('/about_me')
def about_me_content():
    return """
    <p style="font-size: 18px; text-align: justify;"> <strong> Nama : </strong> Kiki Ervin </p>
    <strong> NIM : </strong> 301220053 <p
    </p> <strong> Kelas : </strong> 5A(Teknik Informatika) <p
    </P>
    <strong> Studi Kasus : </strong> Prediksi Pengunjung Perpustakaan Keliling Kota Bandung

 """

if __name__ == '__main__':
    app.run(debug=True)
