import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import { SectionLabel, Skeleton } from "@/components/SharedUI";
import {
    FileUp,
    FileText,
    FileCode,
    Sparkles,
    Trash2,
    ArrowLeft,
    Play,
    Loader2,
    Search,
    BookOpen,
    CheckCircle2,
    X,
    UploadCloud,
    Calendar,
    Layers,
    AlignLeft,
} from "lucide-react";
import { toast } from "sonner";

const ALLOWED_EXTENSIONS = [
    ".pdf",
    ".md",
    ".markdown",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".sql",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".csv",
];

function getFileIcon(filename = "") {
    const ext = "." + filename.split(".").pop().toLowerCase();
    if (ext === ".pdf") return <FileText className="h-5 w-5 text-rose-400" />;
    if ([".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".sql", ".sh"].includes(ext)) {
        return <FileCode className="h-5 w-5 text-emerald-400" />;
    }
    return <FileText className="h-5 w-5 text-blue-400" />;
}

export default function DocumentLibrary() {
    const { docId } = useParams();
    const navigate = useNavigate();

    const [documents, setDocuments] = useState([]);
    const [selectedDoc, setSelectedDoc] = useState(null);
    const [chunks, setChunks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [chunkSearch, setChunkSearch] = useState("");

    // Upload modal state
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [uploadFile, setUploadFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);

    // AI Drill modal state
    const [isDrillOpen, setIsDrillOpen] = useState(false);
    const [drillQuery, setDrillQuery] = useState("");
    const [drillDifficulty, setDrillDifficulty] = useState("Intermediate");
    const [drillLength, setDrillLength] = useState("medium");
    const [generatingDrill, setGeneratingDrill] = useState(false);

    // Fetch documents list
    const fetchDocuments = async () => {
        try {
            setLoading(true);
            const { data } = await api.get("/documents");
            setDocuments(data || []);
        } catch (err) {
            toast.error("Failed to load documents");
        } finally {
            setLoading(false);
        }
    };

    // Fetch single document detail with chunks
    const fetchDocDetail = async (id) => {
        try {
            setLoading(true);
            const { data } = await api.get(`/documents/${id}`);
            setSelectedDoc(data.document);
            setChunks(data.chunks || []);
        } catch (err) {
            toast.error("Document not found");
            navigate("/documents");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (docId) {
            fetchDocDetail(docId);
        } else {
            setSelectedDoc(null);
            setChunks([]);
            fetchDocuments();
        }
    }, [docId]);

    // Handle document deletion
    const handleDelete = async (e, id, name) => {
        e.stopPropagation();
        if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
        try {
            await api.delete(`/documents/${id}`);
            toast.success("Document deleted");
            if (docId === id) {
                navigate("/documents");
            } else {
                setDocuments((prev) => prev.filter((d) => d.id !== id));
            }
        } catch (err) {
            toast.error("Failed to delete document");
        }
    };

    // Handle file upload
    const handleUploadSubmit = async (e) => {
        e.preventDefault();
        if (!uploadFile) {
            toast.error("Please select a file to upload");
            return;
        }

        const formData = new FormData();
        formData.append("file", uploadFile);

        try {
            setUploading(true);
            const { data } = await api.post("/documents", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            toast.success(`Uploaded ${data.filename}! Created ${data.total_chunks} typing passages.`);
            setIsUploadOpen(false);
            setUploadFile(null);
            navigate(`/documents/${data.id}`);
        } catch (err) {
            const detail = err.response?.data?.detail || "Upload failed";
            toast.error(detail);
        } finally {
            setUploading(false);
        }
    };

    // Trigger typing session directly from a chunk
    const handleTypeChunk = (chunk) => {
        navigate("/practice", {
            state: {
                text: chunk.text,
                domain: "Custom Document",
                topic: selectedDoc?.filename || "Document Chunk",
                difficulty: "Intermediate",
                source_type: "document",
                source_document_id: selectedDoc?.id,
            },
        });
    };

    // Trigger RAG AI Drill generation
    const handleGenerateDrill = async () => {
        if (!selectedDoc) return;
        try {
            setGeneratingDrill(true);
            const { data } = await api.post("/documents/generate-drill", {
                document_id: selectedDoc.id,
                query: drillQuery.trim() || null,
                difficulty: drillDifficulty,
                length: drillLength,
            });

            toast.success("AI generated a typing passage grounded in your document!");
            setIsDrillOpen(false);

            navigate("/practice", {
                state: {
                    question: data.question || null,
                    mode: data.mode || (data.question ? "qa" : "passage"),
                    text: data.text,
                    domain: "Custom Document",
                    topic: `${selectedDoc.filename}${drillQuery ? ` · ${drillQuery}` : ""}`,
                    difficulty: drillDifficulty,
                    length: drillLength,
                    notes: data.notes,
                    source_type: "document",
                    source_document_id: selectedDoc.id,
                },
            });
        } catch (err) {
            const msg = err.response?.data?.detail || "Failed to generate AI drill";
            toast.error(msg);
        } finally {
            setGeneratingDrill(false);
        }
    };

    // Filter chunks by search
    const filteredChunks = chunks.filter((c) =>
        c.text.toLowerCase().includes(chunkSearch.toLowerCase())
    );

    return (
        <Layout>
            <div className="max-w-6xl mx-auto px-6 py-8">
                {/* Header breadcrumb & actions */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            {docId ? (
                                <Link
                                    to="/documents"
                                    className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white transition-colors"
                                >
                                    <ArrowLeft className="h-3.5 w-3.5" />
                                    All Documents
                                </Link>
                            ) : (
                                <div className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">
                                    Document Ingestion & RAG
                                </div>
                            )}
                        </div>
                        <h1 className="text-2xl font-mono font-semibold text-white tracking-tight flex items-center gap-2.5">
                            {selectedDoc ? (
                                <>
                                    {getFileIcon(selectedDoc.filename)}
                                    <span className="truncate max-w-lg">{selectedDoc.filename}</span>
                                </>
                            ) : (
                                <>
                                    <BookOpen className="h-6 w-6 text-blue-400" />
                                    My Document Library
                                </>
                            )}
                        </h1>
                        <p className="text-xs text-zinc-400 font-mono mt-1">
                            {selectedDoc
                                ? `${selectedDoc.total_chunks} passages · ${selectedDoc.total_words} words · Uploaded ${new Date(selectedDoc.uploaded_at).toLocaleDateString()}`
                                : "Upload PDF textbooks, lecture notes, or source code to practice typing your own material."}
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        {selectedDoc ? (
                            <>
                                <button
                                    onClick={() => setIsDrillOpen(true)}
                                    data-testid="ai-drill-btn"
                                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 font-mono text-xs glow-blue transition-colors"
                                >
                                    <Sparkles className="h-3.5 w-3.5" />
                                    Generate AI Drill (RAG)
                                </button>
                                <button
                                    onClick={(e) => handleDelete(e, selectedDoc.id, selectedDoc.filename)}
                                    title="Delete document"
                                    className="p-2.5 rounded-lg border border-white/10 hover:border-rose-500/30 hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 transition-colors"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </>
                        ) : (
                            <button
                                onClick={() => setIsUploadOpen(true)}
                                data-testid="upload-document-btn"
                                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 font-mono text-xs glow-blue transition-colors"
                            >
                                <FileUp className="h-4 w-4" />
                                Upload Document
                            </button>
                        )}
                    </div>
                </div>

                {/* Main Content Area */}
                {loading ? (
                    <div className="space-y-4">
                        <Skeleton className="h-24 w-full" />
                        <Skeleton className="h-24 w-full" />
                        <Skeleton className="h-24 w-full" />
                    </div>
                ) : selectedDoc ? (
                    /* Detail View: Chunks list */
                    <div>
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                            <SectionLabel className="mb-0">
                                Passages ({filteredChunks.length} of {chunks.length})
                            </SectionLabel>

                            <div className="relative w-full sm:w-72">
                                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                                <input
                                    type="text"
                                    value={chunkSearch}
                                    onChange={(e) => setChunkSearch(e.target.value)}
                                    placeholder="Search passages..."
                                    className="w-full bg-[#121215] border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50"
                                />
                            </div>
                        </div>

                        {filteredChunks.length === 0 ? (
                            <div className="tf-card p-12 text-center">
                                <AlignLeft className="h-8 w-8 text-zinc-600 mx-auto mb-3" />
                                <div className="font-mono text-sm text-zinc-300">No passages match your filter</div>
                                <div className="text-xs text-zinc-500 font-mono mt-1">Try another search keyword.</div>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {filteredChunks.map((chunk) => (
                                    <div
                                        key={chunk.id}
                                        className="tf-card p-5 hover:border-white/20 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
                                    >
                                        <div className="space-y-2 max-w-3xl">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] uppercase tracking-wider font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-400 border border-white/10">
                                                    Passage #{chunk.index + 1}
                                                </span>
                                                <span className="text-[11px] font-mono text-zinc-500">
                                                    {chunk.word_count} words
                                                </span>
                                            </div>
                                            <p className="font-mono text-xs text-zinc-300 leading-relaxed line-clamp-3">
                                                {chunk.text}
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                                            <button
                                                onClick={() => handleTypeChunk(chunk)}
                                                className="inline-flex items-center gap-1.5 rounded-md bg-white/5 hover:bg-blue-600/20 hover:border-blue-500/40 border border-white/10 px-3 py-2 text-xs font-mono text-zinc-200 hover:text-blue-300 transition-all"
                                            >
                                                <Play className="h-3 w-3 fill-current" />
                                                Type This
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
                    /* List View: All documents */
                    <div>
                        {documents.length === 0 ? (
                            <div className="tf-card p-12 text-center border-dashed border-white/15">
                                <div className="h-14 w-14 rounded-2xl grid place-items-center border border-white/10 bg-white/[0.02] mx-auto mb-4">
                                    <UploadCloud className="h-7 w-7 text-zinc-500" />
                                </div>
                                <h3 className="text-sm font-mono text-white font-medium">No documents uploaded yet</h3>
                                <p className="text-xs text-zinc-500 font-mono mt-1 max-w-sm mx-auto">
                                    Add your own technical PDF, Markdown notes, or code files. TypeForge will parse, chunk, and embed them for typing practice and RAG drills.
                                </p>
                                <button
                                    onClick={() => setIsUploadOpen(true)}
                                    className="mt-6 inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 font-mono text-xs glow-blue transition-colors"
                                >
                                    <FileUp className="h-4 w-4" />
                                    Upload Your First Document
                                </button>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {documents.map((doc) => (
                                    <div
                                        key={doc.id}
                                        onClick={() => navigate(`/documents/${doc.id}`)}
                                        className="tf-card p-5 cursor-pointer hover:border-blue-500/40 hover:bg-blue-500/[0.02] transition-all group flex flex-col justify-between"
                                    >
                                        <div>
                                            <div className="flex items-start justify-between gap-3 mb-3">
                                                <div className="p-2.5 rounded-lg border border-white/10 bg-white/[0.02] group-hover:border-blue-500/30 transition-colors">
                                                    {getFileIcon(doc.filename)}
                                                </div>
                                                <button
                                                    onClick={(e) => handleDelete(e, doc.id, doc.filename)}
                                                    title="Delete"
                                                    className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            </div>

                                            <h3 className="font-mono text-sm text-white font-medium truncate group-hover:text-blue-400 transition-colors">
                                                {doc.filename}
                                            </h3>

                                            <div className="flex items-center gap-3 text-[11px] font-mono text-zinc-500 mt-3">
                                                <span className="flex items-center gap-1">
                                                    <Layers className="h-3 w-3" />
                                                    {doc.total_chunks} passages
                                                </span>
                                                <span>·</span>
                                                <span>{doc.total_words} words</span>
                                            </div>
                                        </div>

                                        <div className="pt-4 mt-4 border-t border-white/5 flex items-center justify-between text-[10px] font-mono text-zinc-500">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {new Date(doc.uploaded_at).toLocaleDateString()}
                                            </span>
                                            <span className="text-blue-400 group-hover:translate-x-0.5 transition-transform">
                                                View chunks →
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Upload Modal */}
                {isUploadOpen && (
                    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
                        <div className="tf-card max-w-lg w-full p-6 relative border-white/15 animate-in fade-in zoom-in-95 duration-150">
                            <button
                                onClick={() => {
                                    setIsUploadOpen(false);
                                    setUploadFile(null);
                                }}
                                className="absolute right-4 top-4 text-zinc-500 hover:text-white"
                            >
                                <X className="h-4 w-4" />
                            </button>

                            <div className="flex items-center gap-2 mb-1">
                                <FileUp className="h-4 w-4 text-blue-400" />
                                <h3 className="font-mono text-base text-white font-medium">Upload Document</h3>
                            </div>
                            <p className="text-xs text-zinc-400 font-mono mb-5">
                                Select or drag a technical document to generate typing chunks.
                            </p>

                            <form onSubmit={handleUploadSubmit}>
                                <div
                                    onDragOver={(e) => {
                                        e.preventDefault();
                                        setDragActive(true);
                                    }}
                                    onDragLeave={() => setDragActive(false)}
                                    onDrop={(e) => {
                                        e.preventDefault();
                                        setDragActive(false);
                                        if (e.dataTransfer.files?.[0]) {
                                            setUploadFile(e.dataTransfer.files[0]);
                                        }
                                    }}
                                    onClick={() => fileInputRef.current?.click()}
                                    className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                                        dragActive
                                            ? "border-blue-500 bg-blue-500/5"
                                            : "border-white/10 hover:border-white/20 bg-white/[0.01]"
                                    }`}
                                >
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept={ALLOWED_EXTENSIONS.join(",")}
                                        onChange={(e) => {
                                            if (e.target.files?.[0]) {
                                                setUploadFile(e.target.files[0]);
                                            }
                                        }}
                                        className="hidden"
                                    />
                                    <UploadCloud className="h-8 w-8 text-zinc-500 mx-auto mb-2" />
                                    {uploadFile ? (
                                        <div className="space-y-1">
                                            <div className="font-mono text-xs text-white font-medium">
                                                {uploadFile.name}
                                            </div>
                                            <div className="text-[10px] text-zinc-500 font-mono">
                                                {(uploadFile.size / 1024).toFixed(1)} KB
                                            </div>
                                        </div>
                                    ) : (
                                        <div>
                                            <div className="font-mono text-xs text-zinc-300">
                                                Click to browse or drop file here
                                            </div>
                                            <div className="text-[10px] text-zinc-500 font-mono mt-1">
                                                Supports PDF, Markdown, TXT, code files (up to 10MB)
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="flex items-center justify-end gap-3 mt-6">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setIsUploadOpen(false);
                                            setUploadFile(null);
                                        }}
                                        className="px-4 py-2 text-xs font-mono text-zinc-400 hover:text-white"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={!uploadFile || uploading}
                                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2 font-mono text-xs glow-blue transition-colors"
                                    >
                                        {uploading ? (
                                            <>
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                Parsing & Embedding…
                                            </>
                                        ) : (
                                            "Upload & Process"
                                        )}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* AI Drill (RAG) Modal */}
                {isDrillOpen && (
                    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
                        <div className="tf-card max-w-lg w-full p-6 relative border-white/15 animate-in fade-in zoom-in-95 duration-150">
                            <button
                                onClick={() => setIsDrillOpen(false)}
                                className="absolute right-4 top-4 text-zinc-500 hover:text-white"
                            >
                                <X className="h-4 w-4" />
                            </button>

                            <div className="flex items-center gap-2 mb-1">
                                <Sparkles className="h-4 w-4 text-blue-400" />
                                <h3 className="font-mono text-base text-white font-medium">Generate AI Drill (RAG)</h3>
                            </div>
                            <p className="text-xs text-zinc-400 font-mono mb-5">
                                Groq will retrieve the most relevant passages from{" "}
                                <span className="text-white font-semibold">{selectedDoc?.filename}</span> and create a tailored typing drill.
                            </p>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] uppercase tracking-wider font-mono text-zinc-400 block mb-1.5">
                                        Focus Area / Concept (Optional)
                                    </label>
                                    <input
                                        type="text"
                                        value={drillQuery}
                                        onChange={(e) => setDrillQuery(e.target.value)}
                                        placeholder="e.g. Virtual Memory, B-Trees, Chapter 2"
                                        className="w-full bg-[#121215] border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50"
                                    />
                                    <p className="text-[10px] text-zinc-500 font-mono mt-1">
                                        If left blank, AI picks the most prominent introductory passages.
                                    </p>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="text-[10px] uppercase tracking-wider font-mono text-zinc-400 block mb-1.5">
                                            Difficulty
                                        </label>
                                        <select
                                            value={drillDifficulty}
                                            onChange={(e) => setDrillDifficulty(e.target.value)}
                                            className="w-full bg-[#121215] border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-blue-500/50"
                                        >
                                            <option value="Beginner">Beginner</option>
                                            <option value="Intermediate">Intermediate</option>
                                            <option value="Advanced">Advanced</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label className="text-[10px] uppercase tracking-wider font-mono text-zinc-400 block mb-1.5">
                                            Length
                                        </label>
                                        <select
                                            value={drillLength}
                                            onChange={(e) => setDrillLength(e.target.value)}
                                            className="w-full bg-[#121215] border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-blue-500/50"
                                        >
                                            <option value="short">Short (~30w)</option>
                                            <option value="medium">Medium (~60w)</option>
                                            <option value="long">Long (~100w)</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="flex items-center justify-end gap-3 mt-6">
                                    <button
                                        type="button"
                                        onClick={() => setIsDrillOpen(false)}
                                        className="px-4 py-2 text-xs font-mono text-zinc-400 hover:text-white"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleGenerateDrill}
                                        disabled={generatingDrill}
                                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2 font-mono text-xs glow-blue transition-colors"
                                    >
                                        {generatingDrill ? (
                                            <>
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                Retrieving & Generating…
                                            </>
                                        ) : (
                                            <>
                                                <Sparkles className="h-3.5 w-3.5" />
                                                Forge Drill
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
}
