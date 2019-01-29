# brioa_port

Tools for interpreting data relating to the seaport in [Itapoá, Brazil](http://www.portoitapoa.com.br/) (UN/LOCODE: BR IOA).

## The tools

**Webcam downloader:** The port administration provides a public [image feed](http://www.portoitapoa.com.br/camera/) from a webcam watching over the berthing areas. This tool makes it easy to download these pictures on a fixed interval, preserving the creation date in the filenames.

**Schedule downloader:** A spreadsheet describing recent and scheduled ship arrivals, moorings, and sailings is made available in the [Programação de Navios](http://www.portoitapoa.com.br/servicos_programacao_navios/) page. This tool processes and inserts this information into an SQLite database, describing the changes in schedule over time for each ship.

**Timelapse creator:** Using the aforementioned webcam and schedule data, this tool creates timelapse videos with augmented information, describing the ships that appear on screen.
