using System;
using System.Diagnostics;
using System.Collections.Generic;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Media.Effects;
using System.Windows.Shapes;
using System.Windows.Threading;
using System.Text.RegularExpressions;

namespace SeasonAwardsScraper
{
    public class ScraperApp : Application
    {
        [STAThread]
        public static void Main()
        {
            ScraperApp app = new ScraperApp();
            app.Run(new MainWindow());
        }
    }

    public class MainWindow : Window
    {
        // Controls
        private Button runButton;
        private Button stopButton;
        private TextBlock statusText;
        private ProgressBar progressBar;
        private StackPanel listPanel; // Vertical List
        
        // Data
        private Dictionary<string, AwardRow> rowsMap = new Dictionary<string, AwardRow>();
        private Process scraperProcess;
        private bool isRunning = false;

        // Awards Data
        private string[] awardsList = new string[] {
            "oscar", "gg", "bafta", "sag", "critics", "afi", "nbr", "venice", 
            "cannes", "annie", "dga", "pga", "lafca", "nyfcc", "wga", "adg", 
            "gotham", "astra", "spirit", "bifa",
            "gen_analysis", // Analysis Step (Runs after scraping)
            "tmdb", "upload"
        };
        
        private Dictionary<string, string> displayNames = new Dictionary<string, string> {
            {"gen_analysis", "ANALYSIS GENERATION"},
            {"oscar", "OSCARS"}, {"gg", "GOLDEN GLOBES"}, {"bafta", "BAFTA"}, {"sag", "SAG AWARDS"},
            {"critics", "CRITICS CHOICE"}, {"afi", "AFI AWARDS"}, {"nbr", "NBR AWARDS"}, {"venice", "VENICE"},
            {"cannes", "CANNES"}, {"annie", "ANNIE AWARDS"}, {"dga", "DGA"}, {"pga", "PGA"},
            {"lafca", "LAFCA"}, {"nyfcc", "NYFCC"}, {"wga", "WGA"}, {"adg", "ADG"},
            {"gotham", "GOTHAM"}, {"astra", "ASTRA / HCA"}, {"spirit", "INDIE SPIRIT"}, {"bifa", "BIFA"},
            {"tmdb", "TMDB IMAGES"}, {"upload", "FIREBASE UPLOAD"}
        };

        private int completedSteps = 0;
        private int totalSteps = 0;
        private Grid summaryGrid; // For the summary table

        public MainWindow()
        {
            this.Title = "Season Awards Scraper";
            this.Width = 1100; // Much wider for side-by-side
            this.SizeToContent = SizeToContent.Height;
            this.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#121212"));
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.WindowStyle = WindowStyle.None;
            this.AllowsTransparency = true;
            this.ResizeMode = ResizeMode.NoResize;

            // Set Icon
            try {
                this.Icon = new BitmapImage(new Uri("pack://siteoforigin:,,,/favicon.jpg"));
            } catch { /* Ignore missing icon */ }

            InitializeUI();
            
            totalSteps = awardsList.Length;
            
            // Initial load of summary if available
            LoadSummary();
        }

        private void InitializeUI()
        {
            Color gold = (Color)ColorConverter.ConvertFromString("#D4A84B");
            Color dark = (Color)ColorConverter.ConvertFromString("#121212");

            // Root Border
            Border rootBorder = new Border();
            rootBorder.BorderBrush = new SolidColorBrush(gold);
            rootBorder.BorderThickness = new Thickness(1);
            rootBorder.Background = new SolidColorBrush(dark);
            
            // Main Vertical Grid (Caption + Content)
            Grid mainGrid = new Grid();
            mainGrid.RowDefinitions.Add(new RowDefinition() { Height = new GridLength(30) }); // Caption
            mainGrid.RowDefinitions.Add(new RowDefinition() { Height = GridLength.Auto });    // Content Body
            
            // 1. Caption Bar
            Border captionBar = new Border();
            captionBar.Background = new SolidColorBrush(Color.FromRgb(30,30,30));
            captionBar.MouseLeftButtonDown += HandleDragMove;
            
            StackPanel captionButtons = new StackPanel();
            captionButtons.Orientation = Orientation.Horizontal;
            captionButtons.HorizontalAlignment = HorizontalAlignment.Right;
            
            Button closeBtn = new Button();
            closeBtn.Content = "X";
            closeBtn.Width = 40;
            closeBtn.Height = 30;
            closeBtn.Background = Brushes.Transparent;
            closeBtn.Foreground = Brushes.White;
            closeBtn.BorderThickness = new Thickness(0);
            closeBtn.Click += HandleClose;
            
            captionButtons.Children.Add(closeBtn);
            captionBar.Child = captionButtons;
            
            Grid.SetRow(captionBar, 0);
            mainGrid.Children.Add(captionBar);

            // 2. Content Body (Side-by-Side)
            Grid bodyGrid = new Grid();
            bodyGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(450) }); // Left: Scraper
            bodyGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1) });   // Sep: Line
            bodyGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) }); // Right: Summary

            // === LEFT PANEL: SCRAPER ===
            Grid leftGrid = new Grid();
            leftGrid.RowDefinitions.Add(new RowDefinition() { Height = new GridLength(90) }); // Header
            leftGrid.RowDefinitions.Add(new RowDefinition() { Height = GridLength.Auto });    // List
            leftGrid.RowDefinitions.Add(new RowDefinition() { Height = new GridLength(35) }); // Status

            // Header
            Border headerBorder = new Border();
            headerBorder.Background = new SolidColorBrush(gold);
            headerBorder.Padding = new Thickness(10);
            
            StackPanel headerStack = new StackPanel();
            headerStack.VerticalAlignment = VerticalAlignment.Center;
            headerStack.HorizontalAlignment = HorizontalAlignment.Center;
            
            TextBlock titleTxt = new TextBlock();
            titleTxt.Text = "SEASON AWARDS 2026";
            titleTxt.FontSize = 22;
            titleTxt.FontWeight = FontWeights.Bold;
            titleTxt.Foreground = Brushes.Black;
            titleTxt.HorizontalAlignment = HorizontalAlignment.Center;
            headerStack.Children.Add(titleTxt);
            
            runButton = new Button();
            runButton.Content = "PLAY  AVVIA SCRAPING";
            runButton.FontSize = 12;
            runButton.FontWeight = FontWeights.Bold;
            runButton.Padding = new Thickness(15, 5, 15, 5);
            runButton.Margin = new Thickness(0, 5, 0, 0);
            runButton.Background = Brushes.Black;
            runButton.Foreground = new SolidColorBrush(gold);
            runButton.BorderThickness = new Thickness(0);
            runButton.HorizontalAlignment = HorizontalAlignment.Center;
            runButton.Click += RunButton_Click;
            headerStack.Children.Add(runButton);

            headerBorder.Child = headerStack;
            Grid.SetRow(headerBorder, 0);
            leftGrid.Children.Add(headerBorder);

            // List
            listPanel = new StackPanel();
            listPanel.Margin = new Thickness(10, 5, 10, 5);
            foreach (string code in awardsList)
            {
                string name = displayNames.ContainsKey(code) ? displayNames[code] : code.ToUpper();
                AwardRow row = new AwardRow(code, name);
                rowsMap[code] = row;
                listPanel.Children.Add(row);
            }
            Grid.SetRow(listPanel, 1);
            leftGrid.Children.Add(listPanel);

            // Status
            Grid statusGrid = new Grid();
            statusGrid.Background = new SolidColorBrush(Color.FromRgb(20,20,20));
            statusGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) });
            statusGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(100) });

            statusText = new TextBlock();
            statusText.Text = "Pronto (0%)";
            statusText.Foreground = Brushes.Gray;
            statusText.VerticalAlignment = VerticalAlignment.Center;
            statusText.Margin = new Thickness(20, 0, 0, 0);
            Grid.SetColumn(statusText, 0);
            statusGrid.Children.Add(statusText);

            stopButton = new Button();
            stopButton.Content = "STOP";
            stopButton.Background = Brushes.Red;
            stopButton.Foreground = Brushes.White;
            stopButton.FontWeight = FontWeights.Bold;
            stopButton.BorderThickness = new Thickness(0);
            stopButton.Margin = new Thickness(5);
            stopButton.IsEnabled = false;
            stopButton.Click += StopButton_Click;
            Grid.SetColumn(stopButton, 1);
            statusGrid.Children.Add(stopButton);

            progressBar = new ProgressBar();
            progressBar.Height = 3;
            progressBar.VerticalAlignment = VerticalAlignment.Bottom;
            progressBar.BorderThickness = new Thickness(0);
            progressBar.Background = Brushes.Transparent;
            progressBar.Foreground = new SolidColorBrush(gold);
            Grid.SetColumnSpan(progressBar, 2);
            statusGrid.Children.Add(progressBar);

            Grid.SetRow(statusGrid, 2);
            leftGrid.Children.Add(statusGrid);

            Grid.SetColumn(leftGrid, 0);
            bodyGrid.Children.Add(leftGrid);

            // === SEPARATOR ===
            Border sep = new Border();
            sep.Background = new SolidColorBrush(gold);
            sep.HorizontalAlignment = HorizontalAlignment.Stretch;
            sep.VerticalAlignment = VerticalAlignment.Stretch;
            sep.Opacity = 0.5; // "Leggerissima"
            Grid.SetColumn(sep, 1);
            bodyGrid.Children.Add(sep);

            // === RIGHT PANEL: SUMMARY ===
            Grid rightGrid = new Grid();
            rightGrid.RowDefinitions.Add(new RowDefinition() { Height = new GridLength(40) }); // Title "Resoconto"
            rightGrid.RowDefinitions.Add(new RowDefinition() { Height = new GridLength(1, GridUnitType.Star) }); // Table

            // Summary Header
            TextBlock summaryTitle = new TextBlock();
            summaryTitle.Text = "RESOCONTO ANNUALE";
            summaryTitle.Foreground = new SolidColorBrush(gold);
            summaryTitle.FontWeight = FontWeights.Bold;
            summaryTitle.FontSize = 16;
            summaryTitle.HorizontalAlignment = HorizontalAlignment.Center;
            summaryTitle.VerticalAlignment = VerticalAlignment.Center;
            Grid.SetRow(summaryTitle, 0);
            rightGrid.Children.Add(summaryTitle);

            ScrollViewer summaryScroll = new ScrollViewer();
            summaryScroll.VerticalScrollBarVisibility = ScrollBarVisibility.Auto;
            summaryGrid = new Grid();
            summaryGrid.Margin = new Thickness(10);
            summaryScroll.Content = summaryGrid;
            
            Grid.SetRow(summaryScroll, 1);
            rightGrid.Children.Add(summaryScroll);

            Grid.SetColumn(rightGrid, 2);
            bodyGrid.Children.Add(rightGrid);

            // Add Body to Main
            Grid.SetRow(bodyGrid, 1);
            mainGrid.Children.Add(bodyGrid);

            rootBorder.Child = mainGrid;
            this.Content = rootBorder;
        }

        private void LoadSummary()
        {
            try {
                string path = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "analysis.json");
                if (!System.IO.File.Exists(path)) return;
                
                string json = System.IO.File.ReadAllText(path);
                RenderSummaryTable(json);
            } catch {}
        }

        private void RenderSummaryTable(string json)
        {
            summaryGrid.Children.Clear();
            summaryGrid.RowDefinitions.Clear();
            summaryGrid.ColumnDefinitions.Clear();

            // Columns: Name, Film, Dir, Actor, Actress
            summaryGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(140) }); // Name
            summaryGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) }); // Film
            summaryGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) }); // Dir
            summaryGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) }); // Actor
            summaryGrid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) }); // Actress

            // Header Row
            AddSummaryRow(-1, "AWARD", "FILM", "DIR", "ACTOR", "ACTRESS", true);

            int rowIdx = 0;
            
            // Extract ROOT expected block
            string expectedRoot = ExtractJsonBlock(json, "expected");
            
            // Extract YEARS block, then 2025_2026
            string yearsBlock = ExtractJsonBlock(json, "years");
            string currentYearBlock = ExtractJsonBlock(yearsBlock, "2025_2026");

            // If no year data yet, still show empty rows
            if (string.IsNullOrEmpty(currentYearBlock)) currentYearBlock = "";

            foreach (string code in awardsList)
            {
                if (code == "gen_analysis" || code == "tmdb" || code == "upload") continue;
                
                string awardName = displayNames.ContainsKey(code) ? displayNames[code] : code.ToUpper();
                
                // Get Award Data for Current Year
                string awardData = ExtractJsonBlock(currentYearBlock, code);
                // Get Expected Data for this Award (Global)
                string awardExpected = ExtractJsonBlock(expectedRoot, code);

                string film = FormatCell(awardData, awardExpected, "best-film");
                string dir = FormatCell(awardData, awardExpected, "best-director");
                string actor = "";
                string actress = "";

                // Combined check
                bool isCombined = (code == "gotham" || code == "bifa" || code == "spirit" || code == "lafca");
                
                if (isCombined) {
                   int a1_noms = GetNominations(awardData, "best-actor");
                   int a2_noms = GetNominations(awardData, "best-actress");
                   
                   int a1_exp = GetExpected(awardExpected, "best-actor"); // base expected
                   // Special overrides for Combined Expected Logic
                   int targetTotal = 0;
                   if (code == "lafca") targetTotal = 8;
                   else if (code == "gotham") targetTotal = 20;
                   else if (code == "bifa") targetTotal = 12; // 2025+
                   else if (code == "spirit") targetTotal = 20;

                   int com = a1_noms + a2_noms;
                   
                   if (com == 0 && targetTotal == 0) actor = "-";
                   else {
                       string color = (com == targetTotal) ? "LightGreen" : "Pending";
                       if (com == 0) color = "Red"; 
                       // We handle color in AddSummaryRow, so just return text here
                       actor = com + "/" + targetTotal;
                   }
                   actress = ""; // Spans 2 cols visually, handled in AddSummaryRow if possible, or just empty
                } else {
                   actor = FormatCell(awardData, awardExpected, "best-actor");
                   actress = FormatCell(awardData, awardExpected, "best-actress");
                }

                AddSummaryRow(rowIdx++, awardName, film, dir, actor, actress, false);
            }
        }

        private string FormatCell(string awardJson, string expectedJson, string cat) {
            int noms = GetNominations(awardJson, cat);
            int exp = GetExpected(expectedJson, cat);

            // Special override for ADG Film
            if (cat == "best-film" && exp == 15) { 
                 // Logic from control.js: if ADG and expected 0/null but should be 15
                 // In json it is 15 so it's fine.
            }
            if (cat == "best-film" && exp == 10) { /* AFI/NBR/PGA often 10+? Logic just uses expected int */ }
            if (cat == "best-film" && exp == 11) { /* AFI usually 10/11 */ }

            if (noms == 0 && exp == 0) return "-";
            return noms + "/" + exp;
        }

        private int GetNominations(string awardJson, string cat) {
             if (string.IsNullOrEmpty(awardJson)) return 0;
             string catBlock = ExtractJsonBlock(awardJson, cat);
             if (string.IsNullOrEmpty(catBlock)) return 0;
             return ExtractInt(catBlock, "nominations");
        }

        private int GetExpected(string expectedJson, string cat) {
             if (string.IsNullOrEmpty(expectedJson)) return 0;
             // Expected block is simple "cat": 10
             // ExtractInt regex expects "key": value
             return ExtractInt(expectedJson, cat);
        }

        private void AddSummaryRow(int rowIdx, string c1, string c2, string c3, string c4, string c5, bool isHeader)
        {
            summaryGrid.RowDefinitions.Add(new RowDefinition() { Height = new GridLength(30) });
            
            int r = rowIdx + 1; // +1 for offset if needed, but header is -1 logic
            if (isHeader) r = 0;
            else r = rowIdx + 1;

            AddCell(r, 0, c1, isHeader, HorizontalAlignment.Left);
            AddCell(r, 1, c2, isHeader, HorizontalAlignment.Center);
            AddCell(r, 2, c3, isHeader, HorizontalAlignment.Center);
            AddCell(r, 3, c4, isHeader, HorizontalAlignment.Center);
            AddCell(r, 4, c5, isHeader, HorizontalAlignment.Center);
        }

        private void AddCell(int row, int col, string text, bool isHeader, HorizontalAlignment align)
        {
            TextBlock tb = new TextBlock();
            tb.Text = text;
            tb.Foreground = isHeader ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#D4A84B")) : Brushes.White;
            tb.FontWeight = isHeader ? FontWeights.Bold : FontWeights.Normal;
            tb.FontSize = isHeader ? 12 : 11;
            tb.VerticalAlignment = VerticalAlignment.Center;
            tb.HorizontalAlignment = align;
            if (col == 0) tb.Margin = new Thickness(10,0,0,0);
            
            // Color logic for values
            if (!isHeader && col > 0 && text != "-") {
                tb.Foreground = Brushes.LightGreen;
                if (text == "0" || text.StartsWith("0/")) tb.Foreground = Brushes.Red;
            } else if (!isHeader && col > 0) {
                 tb.Foreground = Brushes.Gray;
            }

            Grid.SetRow(tb, row);
            Grid.SetColumn(tb, col);
            summaryGrid.Children.Add(tb);
        }

        // ... Existing Events ...
        
        // Update LoadSummary call in ApplyUpdate
        /* In ApplyUpdate inside check for gen_analysis success: */
        // if (award == "gen_analysis") {
        //     rowsMap[award].SetSuccess("Analysis Generated");
        //     LoadSummary(); // Refresh table
        // }


        private void HandleDragMove(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            this.DragMove();
        }

        private void HandleClose(object sender, RoutedEventArgs e)
        {
            if (scraperProcess != null && !scraperProcess.HasExited)
            {
                try { scraperProcess.Kill(); } catch {}
            }
            this.Close();
        }

        private void StopButton_Click(object sender, RoutedEventArgs e)
        {
            if (scraperProcess != null && !scraperProcess.HasExited) 
            {
                 try { scraperProcess.Kill(); } catch {}
            }
        }

        private void RunButton_Click(object sender, RoutedEventArgs e)
        {
            if (isRunning) return;
            isRunning = true;
            runButton.IsEnabled = false;
            runButton.Opacity = 0.5;
            stopButton.IsEnabled = true;
            statusText.Text = "Starting (0%)...";
            progressBar.Value = 0;
            progressBar.IsIndeterminate = false; // Using percentage
            completedSteps = 0;

            foreach (var row in rowsMap.Values) row.Reset();

            Thread t = new Thread(RunProcess);
            t.IsBackground = true;
            t.Start();
        }

        private void RunProcess()
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = "py"; 
                psi.Arguments = "scraper/scrape_and_upload.py";
                psi.UseShellExecute = false;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                psi.CreateNoWindow = true;
                psi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                psi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";

                scraperProcess = new Process();
                scraperProcess.StartInfo = psi;
                
                scraperProcess.OutputDataReceived += OutputHandler;

                scraperProcess.Start();
                scraperProcess.BeginOutputReadLine();
                scraperProcess.BeginErrorReadLine();
                scraperProcess.WaitForExit();

                Application.Current.Dispatcher.Invoke(new Action(ProcessFinished));
            } 
            catch (Exception ex) 
            {
                Application.Current.Dispatcher.Invoke(new Action<string>(ShowError), ex.Message);
            }
        }

        private void OutputHandler(object sender, DataReceivedEventArgs e)
        {
            if (e.Data != null) ParseOutput(e.Data);
        }

        private void ProcessFinished()
        {
            isRunning = false;
            runButton.IsEnabled = true;
            runButton.Opacity = 1;
            stopButton.IsEnabled = false;
            progressBar.IsIndeterminate = false;
            progressBar.Value = 100;
            statusText.Text = "COMPLETATO (100%)";
            
            // Mark ANY unfinished row (Pending OR Running) as Error
            foreach (var row in rowsMap.Values) {
                if (!row.IsFinished()) row.SetError("Incomplete");
            }
        }

        private void ShowError(string msg)
        {
            MessageBox.Show("Error: " + msg);
        }

        private void ParseOutput(string line)
        {
            if (!line.StartsWith("EMIT:")) return;
            
            string json = line.Substring(5);
            
            Application.Current.Dispatcher.Invoke(new Action<string>(ApplyUpdate), json);
        }

        private void ApplyUpdate(string json)
        {
             try {
                string type = ExtractValue(json, "type");
                
                if (type == "award_start") {
                    string award = ExtractValue(json, "award");
                    if (rowsMap.ContainsKey(award)) {
                         rowsMap[award].SetRunning();
                         statusText.Text = rowsMap[award].DisplayName + "...";
                    }
                } 
                else if (type == "award_finish") {
                    string award = ExtractValue(json, "award");
                    string successStr = ExtractValueBool(json, "success");
                    
                    if (rowsMap.ContainsKey(award)) {
                         if (successStr == "true") {
                            string statsStr = ExtractJsonBlock(json, "stats");
                            int countFilm = ExtractInt(statsStr, "best-film");
                            int countDir = ExtractInt(statsStr, "best-director");
                            
                            // Calculate Actor Stats
                            int countActors = 0;
                            countActors += ExtractInt(statsStr, "best-actor");
                            countActors += ExtractInt(statsStr, "best-actress");
                            countActors += ExtractInt(statsStr, "best-supporting-actor");
                            countActors += ExtractInt(statsStr, "best-supporting-actress");
                            countActors += ExtractInt(statsStr, "best-performance");
                            countActors += ExtractInt(statsStr, "breakthrough-performance");
                            
                            if (award == "gen_analysis") {
                                rowsMap[award].SetSuccess("Analysis Generated");
                                LoadSummary(); // Refresh table
                            } else {
                                if (countFilm == 0 && countDir == 0 && countActors == 0) {
                                    rowsMap[award].SetError("No Data"); 
                                } else {
                                    string info = String.Format("{0} Films, {1} Dirs, {2} Actors", countFilm, countDir, countActors);
                                    rowsMap[award].SetSuccess(info);
                                }
                            }
                         } else {
                            string err = ExtractValue(json, "error");
                            rowsMap[award].SetError(err);
                         }
                        
                         UpdateProgress();
                    }
                }
                else if (type == "tmdb_start") {
                     if (rowsMap.ContainsKey("tmdb")) rowsMap["tmdb"].SetRunning();
                     statusText.Text = "Downloading Images...";
                }
                else if (type == "tmdb_finish") {
                     string total = ExtractValue(json, "total_updated");
                     if (rowsMap.ContainsKey("tmdb")) {
                         rowsMap["tmdb"].SetSuccess(total + " Images");
                         UpdateProgress();
                     }
                }
                else if (type == "upload_start") {
                     if (rowsMap.ContainsKey("upload")) rowsMap["upload"].SetRunning();
                     statusText.Text = "Uploading...";
                }
                else if (type == "pipeline_finish") {
                     if (rowsMap.ContainsKey("upload")) {
                         rowsMap["upload"].SetSuccess("Done");
                         UpdateProgress();
                     }
                }
             } catch {}
        }

        private void UpdateProgress() {
            completedSteps++;
            if (completedSteps > totalSteps) completedSteps = totalSteps;
            int pct = (int)((double)completedSteps / totalSteps * 100);
            
            progressBar.Value = pct;
            
            // Keep current text but update %
            string current = statusText.Text;
            int idx = current.IndexOf("(");
            if (idx > -1) current = current.Substring(0, idx).Trim();
            statusText.Text = current + " (" + pct + "%)";
        }

        // Helpers
        private string ExtractValue(string json, string key) {
            var match = Regex.Match(json, "\"" + key + "\":\\s*\"(.*?)\"");
            return match.Success ? match.Groups[1].Value : "";
        }
        private string ExtractValueBool(string json, string key) {
            var match = Regex.Match(json, "\"" + key + "\":\\s*(true|false)");
            return match.Success ? match.Groups[1].Value : "false";
        }
        private int ExtractInt(string json, string key) {
             var match = Regex.Match(json, "\"" + key + "\":\\s*(\\d+)");
             return match.Success ? int.Parse(match.Groups[1].Value) : 0;
        }
        private string ExtractJsonBlock(string json, string key) {
             int idx = json.IndexOf("\"" + key + "\":");
             if (idx == -1) return "";
             
             // Find start brace
             int start = json.IndexOf("{", idx);
             if (start == -1) return "";
             
             int openBraces = 0;
             int end = -1;
             
             // Scan for matching closing brace
             for (int i = start; i < json.Length; i++) {
                 if (json[i] == '{') openBraces++;
                 else if (json[i] == '}') {
                     openBraces--;
                     if (openBraces == 0) {
                         end = i;
                         break;
                     }
                 }
             }
             
             if (end > -1) return json.Substring(start, end - start + 1);
             return "";
        }
    }

    // === Custom Award Row (Compact List Item) ===
    public class AwardRow : Border
    {
        public string DisplayName { get; private set; }
        private TextBlock statusIcon;
        private TextBlock titleBlock;
        private TextBlock infoBlock;
        private bool isFinished = false; // New flag to track completion
        
        public AwardRow(string code, string name)
        {
            this.DisplayName = name;
            this.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E1E1E"));
            this.CornerRadius = new CornerRadius(4);
            this.Margin = new Thickness(5, 1, 5, 1); // Reduced vertical margin
            this.Padding = new Thickness(15, 6, 15, 6); // Reduced padding
            this.Height = 32; // Reduced height

            Grid grid = new Grid();
            // Columns: [Name *] [Info Auto] [Icon Fixed]
            grid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(140) });
            grid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition() { Width = new GridLength(40) });

            // 1. Title
            titleBlock = new TextBlock();
            titleBlock.Text = name;
            titleBlock.FontSize = 11; // Slightly smaller
            titleBlock.FontWeight = FontWeights.Bold;
            titleBlock.Foreground = Brushes.White;
            titleBlock.VerticalAlignment = VerticalAlignment.Center;
            Grid.SetColumn(titleBlock, 0);
            grid.Children.Add(titleBlock);

            // 2. Info
            infoBlock = new TextBlock();
            infoBlock.Text = "";
            infoBlock.FontSize = 10;
            infoBlock.Foreground = Brushes.Gray;
            infoBlock.VerticalAlignment = VerticalAlignment.Center;
            infoBlock.HorizontalAlignment = HorizontalAlignment.Right;
            infoBlock.Margin = new Thickness(0,0,10,0);
            Grid.SetColumn(infoBlock, 1);
            grid.Children.Add(infoBlock);

            // 3. Icon
            statusIcon = new TextBlock();
            statusIcon.Text = ""; 
            statusIcon.FontSize = 12;
            statusIcon.FontWeight = FontWeights.Bold;
            statusIcon.Foreground = Brushes.Gray;
            statusIcon.VerticalAlignment = VerticalAlignment.Center;
            statusIcon.HorizontalAlignment = HorizontalAlignment.Center;
            Grid.SetColumn(statusIcon, 2);
            grid.Children.Add(statusIcon);

            this.Child = grid;
            Reset();
        }

        public bool IsFinished() { return isFinished; }

        public void Reset() {
            isFinished = false;
            infoBlock.Text = "";
            statusIcon.Text = "";
            this.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E1E1E"));
        }
        public void SetRunning() {
            infoBlock.Text = "Running...";
            statusIcon.Text = "@";
            statusIcon.Foreground = Brushes.Yellow;
            this.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#2A2A20"));
        }
        public void SetSuccess(string text) {
            isFinished = true;
            infoBlock.Text = text;
            statusIcon.Text = "V";
            statusIcon.Foreground = Brushes.LightGreen;
            this.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#202A20"));
        }
        public void SetError(string err) {
            isFinished = true;
            infoBlock.Text = string.IsNullOrEmpty(err) ? "Error" : err;
            statusIcon.Text = "X";
            statusIcon.Foreground = Brushes.Red;
            this.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#2A2020"));
        }
    }
}
